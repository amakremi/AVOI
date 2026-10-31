"""Stage-3 orchestration (freeze / adequacy / confirm), following the Stage-2 pattern.

  python experiments/stage3/run_stage3.py freeze    -> results/stage3/EXPERIMENT_FREEZE_STAGE3.json
  python experiments/stage3/run_stage3.py adequacy  -> WP1 IAM + WP2 AIT/CERT adequacy -> ADEQUACY_DECISIONS_STAGE3.json
  python experiments/stage3/run_stage3.py confirm   -> WP1 + WP2 confirmation (requires both frozen files)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "stage3"))

from common import sha256_file  # noqa: E402

S3 = ROOT / "results" / "stage3"
FREEZE = S3 / "EXPERIMENT_FREEZE_STAGE3.json"
DECISIONS = S3 / "ADEQUACY_DECISIONS_STAGE3.json"

FROZEN_FILES = [
    "config/stage3.yaml", "config/model_adequacy.yaml", "config/loss_matrix.yaml", "config/hyperparameters.yaml",
    "config/assurance_objectives.yaml", "config/evidence_actions.yaml",
    "config/scenario_generator_stage3_dev.yaml", "config/scenario_generator_stage3_val.yaml", "config/scenario_generator_stage3_conf.yaml",
    "docs/STAGE3_REUSE_MAP.md", "docs/STAGE3_EXTERNAL_MODELS.md",
    "src/avoi/adequacy.py", "src/avoi/agent.py", "src/avoi/avoi.py", "src/avoi/bayes_risk.py", "src/avoi/costs.py",
    "src/avoi/models/tan.py", "src/avoi/models/discriminative.py", "src/avoi/datasets/common.py",
    "src/avoi/datasets/iam.py", "src/avoi/datasets/ait.py", "src/avoi/datasets/ait_episodes.py", "src/avoi/datasets/cert.py",
    "src/avoi/evaluation/engine.py", "src/avoi/evaluation/stage2.py", "src/avoi/evaluation/stage3.py",
    "src/avoi/evaluation/stage3_wp1.py", "src/avoi/evaluation/stage3_wp2.py", "src/avoi/evaluation/labels.py",
    "testbed/scenarios/generator.py", "testbed/oracle.py", "testbed/evidence_collectors/collectors.py",
    "experiments/stage3/run_stage3.py", "experiments/stage3/run_wp1.py", "experiments/stage3/run_wp2_ait.py",
    "experiments/stage3/run_wp2_cert.py",
]
DATA_GLOBS = [
    "data/processed/iam_stage3_dev/evidence_store/*.json", "data/processed/iam_stage3_dev/ground_truth/*.json",
    "data/processed/iam_stage3_val/evidence_store/*.json", "data/processed/iam_stage3_val/ground_truth/*.json",
    "data/processed/iam_stage3_conf/evidence_store/*.json", "data/processed/iam_stage3_conf/ground_truth/*.json",
    "data/processed/iam/evidence_store/*.json", "data/processed/iam_stage2/evidence_store/*.json",
    "data/processed/ait/evidence_store.json", "data/processed/ait_stage2/evidence_store.json", "data/processed/ait_stage3/evidence_store.json",
    "data/processed/cert/evidence_store.json", "data/processed/cert_stage2/evidence_store.json",
    "data/processed/cert_stage3_r4_1/evidence_store.json", "data/processed/cert_stage3_r5_1/evidence_store.json",
    # r6.1/r6.2 intentionally excluded - see config/stage3.yaml wp2.cert.new_releases and docs/STAGE3_EXTERNAL_MODELS.md §2b
]
WP1_OBJECTIVES = ["IAM-01-MFA-PRIV", "IAM-02-TERM-DISABLED", "IAM-03-PRIV-AUTHZ"]
WP2_AIT_CLAIMS = ["AIT-EXFIL", "AIT-INTRUSION"]
WP2_CERT_CLAIM = "CERT-INSIDER"


def hashes() -> dict:
    files = {f: sha256_file(ROOT / f) for f in FROZEN_FILES}
    data = {}
    for g in DATA_GLOBS:
        base, pat = g.rsplit("/", 1)
        d = ROOT / base
        paths = sorted(d.glob(pat)) if d.exists() else []
        h = hashlib.sha256()
        for p in paths:
            h.update(p.name.encode()); h.update(sha256_file(p).encode())
        data[g] = {"n_files": len(paths), "sha256": h.hexdigest()}
    return {"files": files, "data": data,
            "combined_sha256": hashlib.sha256(json.dumps({"files": files, "data": data}, sort_keys=True).encode()).hexdigest()}


def verify_freeze() -> dict:
    fr = json.loads(FREEZE.read_text(encoding="utf-8"))
    now = hashes()
    changed = [f for f, h in fr["hashes"]["files"].items() if now["files"].get(f) != h]
    changed += [g for g, h in fr["hashes"]["data"].items() if now["data"].get(g) != h]
    if changed:
        raise SystemExit(f"Stage-3 frozen protocol changed: {changed}")
    return fr


def load_decisions() -> dict:
    body = json.loads(DECISIONS.read_text(encoding="utf-8"))
    chk = hashlib.sha256(json.dumps(body["decisions"], sort_keys=True, default=float).encode()).hexdigest()
    if chk != body["decisions_sha256"]:
        raise SystemExit("Stage-3 adequacy decisions modified after freezing")
    return body["decisions"]


def do_freeze():
    if FREEZE.exists():
        raise SystemExit("Stage-3 freeze exists; create a versioned corrected freeze instead of overwriting.")
    import yaml
    S3.mkdir(parents=True, exist_ok=True)
    pre = json.loads((ROOT / "results/archive/pre_stage3_snapshot/MANIFEST.json").read_text(encoding="utf-8"))
    rec = {"frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "statement": "Stage-3 protocol frozen before any Stage-3 adequacy validation or confirmation evaluation.",
           "pre_stage3_snapshot_commit": pre["git_commit"],
           "stage2_freeze_sha256": pre["stage2_freeze_sha256"], "stage2_decisions_sha256": pre["stage2_decisions_sha256"],
           "model_adequacy_yaml_sha256_unchanged": pre["model_adequacy_yaml_sha256"],
           "stage3_protocol": yaml.safe_load((ROOT / "config/stage3.yaml").read_text(encoding="utf-8")),
           "wp1_objectives": WP1_OBJECTIVES, "wp2_ait_claims": WP2_AIT_CLAIMS, "wp2_cert_claim": WP2_CERT_CLAIM,
           "required_tables": ["table_adaptive_selection_stage3", "table_external_adequacy_stage3", "table_external_avoi_stage3",
                               "table_fixed_horizon_stage3", "table_normal_operation_stage3", "table_feature_stability_stage3",
                               "table_zero_shot_vs_target_stage3"],
           "analysis_code_note": "CSV export code reads saved raw outputs and does not change them",
           "hashes": hashes()}
    FREEZE.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print("Stage-3 freeze:", rec["hashes"]["combined_sha256"], "freeze-file sha256:", sha256_file(FREEZE))


def do_adequacy():
    verify_freeze()
    if DECISIONS.exists():
        raise SystemExit("Stage-3 adequacy decisions already frozen.")
    import run_wp1
    import run_wp2_ait
    decisions = {}
    wp1_recs = run_wp1.adequacy_phase()
    for oid, rec in wp1_recs.items():
        decisions[f"iam|{oid}"] = rec["decision"]
    ait_recs = run_wp2_ait.adequacy_phase()
    for claim, rec in ait_recs.items():
        decisions[f"ait|{claim}"] = rec["decision"]
    try:
        import run_wp2_cert
        cert_rec = run_wp2_cert.adequacy_phase()
        decisions[f"cert|{WP2_CERT_CLAIM}"] = cert_rec["decision"]
    except FileNotFoundError as exc:
        print("WARNING: CERT Stage-3 data not ready, skipping CERT adequacy:", exc, flush=True)
    body = {"frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "decisions": decisions}
    body["decisions_sha256"] = hashlib.sha256(json.dumps(decisions, sort_keys=True, default=float).encode()).hexdigest()
    DECISIONS.write_text(json.dumps(body, indent=1, default=float), encoding="utf-8")
    print("Stage-3 adequacy decisions frozen:", body["decisions_sha256"])


def do_confirm():
    verify_freeze()
    load_decisions()
    import run_wp1
    import run_wp2_ait
    run_wp1.confirm()
    run_wp2_ait.confirm()
    try:
        import run_wp2_cert
        run_wp2_cert.confirm()
    except FileNotFoundError as exc:
        print("WARNING: CERT Stage-3 confirmation skipped:", exc, flush=True)


if __name__ == "__main__":
    {"freeze": do_freeze, "adequacy": do_adequacy, "confirm": do_confirm}[sys.argv[1]]()
