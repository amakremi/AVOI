"""STAGE 3 shared utilities (reuse-first).

Stage-2 pipeline functions (avoi.evaluation.stage2) are reused unchanged; Stage 3 registers its own partitions in the
Stage-2 partition cache under new domain keys and adds only:
  * concatenation of development sources with source-prefixed groups,
  * a monotone-calibrator safeguard around the reused Stage-2 development step,
  * label-blind hash splits for new external data.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import yaml

from avoi import adequacy as AQ
from avoi.datasets.common import ObjectiveData
from avoi.evaluation import stage2 as S
from avoi.evaluation.labels import load_labels

ROOT = Path(__file__).resolve().parents[3]
S3 = ROOT / "results" / "stage3"


def cfg3() -> dict:
    return yaml.safe_load((ROOT / "config" / "stage3.yaml").read_text(encoding="utf-8"))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def hash_fraction(*keys) -> int:
    """Deterministic label-blind bucket 0..99."""
    return int(hashlib.sha256("|".join(map(str, keys)).encode()).hexdigest(), 16) % 100


# ====================================================================================== data
def concat(datas: list[ObjectiveData], sources: list[str], domain: str) -> ObjectiveData:
    """Concatenate ObjectiveData of the same objective; groups become '<source>:<group>' (never collide across sources)."""
    d0 = datas[0]
    for d in datas[1:]:
        assert [a.action_id for a in d.actions] == [a.action_id for a in d0.actions], "action sets differ"
    keys = set.intersection(*[set(d.strata) for d in datas])
    return ObjectiveData(
        domain, d0.objective_id, d0.actions, np.concatenate([d.episode_ids for d in datas]),
        np.concatenate([np.array([f"{s}:{g}" for g in d.groups]) for d, s in zip(datas, sources)]),
        {k: np.concatenate([d.strata[k] for d in datas]) for k in keys} | {"source": np.concatenate([np.full(d.n, s) for d, s in zip(datas, sources)])},
        d0.kind, np.concatenate([d.values for d in datas]), np.concatenate([d.seconds for d in datas]),
        np.concatenate([d.records for d in datas]), np.concatenate([d.bytes_ for d in datas]),
        sum([list(d.privacy) for d in datas], []),
        sum([list(d.provenance) for d in datas], []) if all(d.provenance for d in datas) else None, d0.source_name)


def iam_partitions(include_confirmation: bool) -> dict:
    """WP1 partitions registered as Stage-2 domain 'iam_s3'. Confirmation is loaded only when explicitly requested."""
    from avoi.datasets.iam import load_iam
    c = cfg3()["wp1"]
    key = "iam_s3" + ("" if include_confirmation else "_noconf")
    if key in S._CACHE:
        return S._CACHE[key]
    def store_ready(spec):
        p = ROOT / spec["store"]
        return p.exists() and any(f.stem.startswith(("s3dev-", "s3val-", "s3conf-", "scn-", "s2scn-")) for f in p.glob("*.json"))

    dev_specs = c["data"]["development"]["historical"] + [c["data"]["development"]["new"]]
    loaded = [(load_iam(s["store"], "iam_s3"), s) for s in dev_specs]
    val = (load_iam(c["data"]["validation"]["store"], "iam_s3"), c["data"]["validation"]) if store_ready(c["data"]["validation"]) else None
    conf = (load_iam(c["data"]["confirmation"]["store"], "iam_s3"), c["data"]["confirmation"]) if include_confirmation and store_ready(c["data"]["confirmation"]) else None
    out = {}
    for oid in c["objectives"]:
        ds = [x[0][oid] for x in loaded]
        ys = [load_labels(x[1]["labels"], x[0][oid].episode_ids) for x in loaded]
        dev = concat(ds, [x[1]["source"] for x in loaded], "iam_s3")
        part = {"dev": (dev, np.concatenate(ys), dev.groups)}
        for name, pack in (("val", val), ("conf", conf)):
            if pack is None:
                continue
            d = concat([pack[0][oid]], [pack[1]["source"]], "iam_s3")
            part[name] = (d, load_labels(pack[1]["labels"], d.episode_ids), d.groups)
        out[oid] = part
    S._CACHE[key] = out
    S._CACHE["iam_s3"] = out            # domain key used by the reused Stage-2 develop/validate functions
    return out


# ====================================================================================== development with monotone safeguard
def is_monotone(cal: AQ.Calibrator, grid: int = 999) -> bool:
    p = np.linspace(0.0005, 0.9995, grid)
    q = cal.transform(p)
    return bool(np.all(np.diff(q) >= -1e-9)) and bool(q[-1] > q[0] or cal.method == "none" or np.ptp(q) == 0)


def monotone_calibrator(p, y, groups, candidates, seed) -> tuple[str, dict, AQ.Calibrator, list[str]]:
    """Reused Stage-2 selection (grouped CV log loss) restricted to monotone non-decreasing maps fitted on the same data."""
    name, scores = AQ.select_calibrator(p, y, groups, candidates, seed=seed)
    rejected = []
    for cand in sorted(scores, key=lambda k: scores[k]):
        cal = AQ.Calibrator(cand).fit(p, y)
        if is_monotone(cal):
            return cand, scores, cal, rejected
        rejected.append(cand)
    return "none", scores, AQ.Calibrator("none").fit(p, y), rejected


def develop(domain: str, oid: str, C: dict) -> dict:
    """Reused Stage-2 develop(); if its selected calibrator is non-monotone, re-select among monotone maps (logged)."""
    dev = S.develop(domain, oid, C)
    sel = dev["selection"]
    cal = dev["primary"].cal
    rejected = []
    if not is_monotone(cal):
        oof = dev["oof"]
        name, _, cal, rejected = monotone_calibrator(oof["p"].to_numpy(), oof["y"].to_numpy(), oof["group"].to_numpy(),
                                                     C["adequacy"]["calibration_candidates"], C["adequacy"]["bootstrap"]["seed"])
        base = dev["base"]
        model_id = dev["primary"].model_id.rsplit("+", 1)[0] + "+" + name
        dev["primary"] = AQ.CalibratedEvidenceModel(base, cal, model_id)
        sel["selected_calibrator"], sel["calibrator_params"] = name, cal.params
    sel["rejected_non_monotone_calibrators"] = rejected
    return dev


def save_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=float), encoding="utf-8")
