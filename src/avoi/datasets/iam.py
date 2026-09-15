"""Loader for the controlled IAM testbed evidence store (data/processed/iam/evidence_store)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import yaml

from avoi.actions import ActionSpec
from avoi.datasets.common import ObjectiveData

ROOT = Path(__file__).resolve().parents[3]
STORE = ROOT / "data" / "processed" / "iam" / "evidence_store"
POL = {"supports_satisfied": 1, "supports_violated": -1, "neutral": 0}


def objective_config() -> dict:
    return yaml.safe_load((ROOT / "config" / "assurance_objectives.yaml").read_text(encoding="utf-8"))


def action_catalogue() -> dict:
    return yaml.safe_load((ROOT / "config" / "evidence_actions.yaml").read_text(encoding="utf-8"))["iam_actions"]


def load_iam(store_dir: str | None = None, domain: str = "iam") -> dict[str, ObjectiveData]:
    cfg, cat = objective_config(), action_catalogue()
    store = ROOT / store_dir if store_dir else STORE
    files = sorted(p for p in store.glob("*.json") if p.stem.startswith(("scn-", "s2scn-")))
    stores = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    out = {}
    for obj in cfg["objectives"]:
        specs = [ActionSpec(a["id"], obj["id"], cat[a["id"]]["source_type"], tuple(a["outcomes"].keys()),
                            tuple(POL[v] for v in a["outcomes"].values()), tuple(cat[a["id"]]["privacy"]))
                 for a in obj["actions"]]
        n, m = len(stores), len(specs)
        values = np.zeros((n, m), dtype=int)
        sec, rec, byt = np.zeros((n, m)), np.zeros((n, m)), np.zeros((n, m))
        priv, prov = [], []
        for i, st in enumerate(stores):
            prow, vrow = [], []
            for j, sp in enumerate(specs):
                ob = st["observations"][sp.action_id]
                values[i, j] = sp.outcomes.index(ob["outcome"])
                sec[i, j], rec[i, j], byt[i, j] = ob["acquisition_seconds"], ob["records"], ob["bytes_read"]
                prow.append(list(ob["privacy_categories"]))
                vrow.append({"timestamp_utc": ob["timestamp_utc"], "scope": ob["scope"], "raw_artifact_ref": ob["raw_artifact_ref"],
                             "parser": ob["parser"], "collector": ob["provenance"]["collector"],
                             "assessment_time_ms": ob["provenance"]["assessment_time_ms"]})
            priv.append(prow)
            prov.append(vrow)
        ids = np.array([f"{st['scenario_id']}|{obj['id']}" for st in stores])
        fam = np.array([st["family_id"] for st in stores])
        pol = np.array([sp.polarity for sp in specs], dtype=object)
        full_pol = np.array([[specs[j].polarity[values[i, j]] for j in range(m)] for i in range(n)])
        conflict = (full_pol == 1).any(1) & (full_pol == -1).any(1)
        out[obj["id"]] = ObjectiveData(domain, obj["id"], specs, ids, fam,
                                       {"scenario": np.array([st["scenario_id"] for st in stores]), "conflict": conflict},
                                       "categorical", values, sec, rec, byt, priv, prov, "controlled-iam-testbed")
    return out
