"""Controlled IAM testbed pipeline: generate -> apply -> collect evidence -> oracle ground truth.

Usage:
    python -m testbed.run_testbed --start 0 --end 320 [--keep-realms 3]

Outputs:
    data/processed/iam/evidence_store/<scenario>.json   all evidence observations (outcomes, raw artifacts, costs, privacy)
    data/processed/iam/ground_truth/<scenario>.json     oracle labels + diagnostic detail  (RESTRICTED: evaluation only)
    data/processed/iam/scenario_index.csv               scenario -> family (grouping), no labels
    data/processed/iam/collection_log.jsonl             timings / setup warnings
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import traceback
from pathlib import Path

import yaml

from testbed.evidence_collectors.collectors import IAMCollectors
from testbed.keycloak.applier import Applier
from testbed.keycloak.kc import KeycloakAdmin
from testbed.oracle import evaluate
from testbed.scenarios.generator import generate_spec, load_cfg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "iam"
ASSESSOR = ROOT / "testbed" / "state" / "assessor"


def objectives_cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "assurance_objectives.yaml").read_text(encoding="utf-8"))


def action_order(cfg: dict) -> list[tuple[str, str]]:
    pairs = [(o["id"], a["id"]) for o in cfg["objectives"] for a in o["actions"]]
    # active TEST actions run last so that their login events (>= T0) can never influence other evidence
    return sorted(pairs, key=lambda p: p[1].startswith("test_"))


def run_scenario(i: int, gen_cfg: dict, obj_cfg: dict, kc: KeycloakAdmin, keep: bool, prefix: str = "scn") -> dict:
    spec = generate_spec(i, gen_cfg, prefix)
    realm = spec["scenario_id"]
    t_start = time.time()
    applier = Applier(kc)
    info = applier.apply(spec)
    t_applied = time.time()
    (ASSESSOR / realm).mkdir(parents=True, exist_ok=True)
    (ASSESSOR / realm / "test_credentials.json").write_text(json.dumps({"password": spec["password"]}), encoding="utf-8")
    params = obj_cfg["assessment_parameters"]
    col = IAMCollectors(realm, info["t0_ms"], params, kc, test_password=spec["password"])
    observations = {}
    for obj_id, action_id in action_order(obj_cfg):
        ts = time.time()
        t_perf = time.perf_counter()
        obs = col.collect(action_id)
        obs["acquisition_seconds"] = round(time.perf_counter() - t_perf, 6)
        obs.update({"action_id": action_id, "objective_id": obj_id, "source": "controlled-iam-testbed",
                    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
                    "scope": f"realm:{realm}", "provenance": {"realm": realm, "assessment_time_ms": info["t0_ms"],
                                                              "collector": obs["parser"]},
                    "raw_artifact_ref": f"{OUT.relative_to(ROOT).as_posix()}/evidence_store/{realm}.json#/observations/{action_id}/raw"})
        allowed = {o["id"]: {a["id"]: a["outcomes"] for a in o["actions"]} for o in obj_cfg["objectives"]}[obj_id][action_id]
        if obs["outcome"] not in allowed:
            raise ValueError(f"{realm} {action_id}: outcome {obs['outcome']} not declared in config")
        observations[action_id] = obs
    t_collected = time.time()
    truth = evaluate(realm, params, kc)
    t_oracle = time.time()
    (OUT / "evidence_store").mkdir(parents=True, exist_ok=True)
    (OUT / "ground_truth").mkdir(parents=True, exist_ok=True)
    (OUT / "evidence_store" / f"{realm}.json").write_text(json.dumps({
        "scenario_id": realm, "family_id": spec["family_id"], "assessment_time_ms": info["t0_ms"],
        "observations": observations}, indent=1), encoding="utf-8")
    (OUT / "ground_truth" / f"{realm}.json").write_text(json.dumps({"scenario_id": realm, **truth}, indent=1), encoding="utf-8")
    if not keep:
        kc.delete(f"/{realm}")
    return {"scenario_id": realm, "family_id": spec["family_id"], "seed": spec["seed"],
            "apply_s": round(t_applied - t_start, 2), "collect_s": round(t_collected - t_applied, 2),
            "oracle_s": round(t_oracle - t_collected, 2), "setup_log": info["setup_log"], "labels": truth["labels"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--keep-realms", type=int, default=2, help="keep the last N realms alive for live-mode checks")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--gen-config", default="config/scenario_generator.yaml")
    ap.add_argument("--out-dir", default="data/processed/iam")
    ap.add_argument("--id-prefix", default="scn")
    ap.add_argument("--quiet-labels", action="store_true", help="do not print label counts (Stage-3 confirmation runs)")
    args = ap.parse_args()
    global OUT
    OUT = ROOT / args.out_dir
    gen_cfg, obj_cfg = load_cfg(args.gen_config), objectives_cfg()
    end = args.end if args.end is not None else gen_cfg["n_families"] * gen_cfg["scenarios_per_family"]
    kc = KeycloakAdmin()
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "scenario_index.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario_id", "scenario_index", "family_id"])
        for i in range(gen_cfg["n_families"] * gen_cfg["scenarios_per_family"]):
            w.writerow([f"{args.id_prefix}-{i:04d}", i, i // gen_cfg["scenarios_per_family"]])
    log = (OUT / "collection_log.jsonl").open("a", encoding="utf-8")
    for i in range(args.start, end):
        realm = f"{args.id_prefix}-{i:04d}"
        if args.skip_existing and (OUT / "ground_truth" / f"{realm}.json").exists():
            continue
        for attempt in range(3):
            try:
                rec = run_scenario(i, gen_cfg, obj_cfg, kc, keep=i >= end - args.keep_realms, prefix=args.id_prefix)
                rec["labels_logged"] = False
                labels = rec.pop("labels")
                log.write(json.dumps(rec) + "\n")
                log.flush()
                print(f"{realm} ok apply={rec['apply_s']}s collect={rec['collect_s']}s oracle={rec['oracle_s']}s "
                      f"warnings={len(rec['setup_log'])}" + ("" if args.quiet_labels else f" sat={sum(labels.values())}/6"), flush=True)
                break
            except Exception as exc:
                print(f"{realm} attempt {attempt + 1} FAILED: {exc}", flush=True)
                traceback.print_exc()
                time.sleep(5)
        else:
            log.write(json.dumps({"scenario_id": realm, "status": "failed"}) + "\n")


if __name__ == "__main__":
    main()
