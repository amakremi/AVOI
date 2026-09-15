"""Stage-2 orchestration.

  python experiments/run_stage2.py freeze      -> results/stage2/EXPERIMENT_FREEZE_STAGE2.json (before any Stage-2 label use)
  python experiments/run_stage2.py adequacy    -> develop models + adequacy validation -> results/stage2/ADEQUACY_DECISIONS.json
  python experiments/run_stage2.py confirm     -> confirmation evaluation (requires both frozen files, verifies hashes)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from common import ROOT, sha256_file

S2 = ROOT / "results" / "stage2"
FREEZE = S2 / "EXPERIMENT_FREEZE_STAGE2.json"
DECISIONS = S2 / "ADEQUACY_DECISIONS.json"
TASKS = [("iam", o) for o in ("IAM-01-MFA-PRIV", "IAM-02-TERM-DISABLED", "IAM-03-PRIV-AUTHZ", "IAM-04-DORMANT",
                               "IAM-05-BREAKGLASS", "IAM-06-ACCESS-REVIEW")] + [("ait", "AIT-EXFIL"), ("ait", "AIT-INTRUSION"), ("cert", "CERT-INSIDER")]

FROZEN_FILES = [
    "config/model_adequacy.yaml", "config/stage2.yaml", "config/loss_matrix.yaml", "config/hyperparameters.yaml",
    "config/assurance_objectives.yaml", "config/evidence_actions.yaml", "config/scenario_generator_stage2.yaml",
    "docs/STAGE2_HYPOTHESES.md", "docs/PREREGISTERED_HYPOTHESES.md",
    "src/avoi/adequacy.py", "src/avoi/agent.py", "src/avoi/avoi.py", "src/avoi/bayes_risk.py", "src/avoi/costs.py",
    "src/avoi/actions.py", "src/avoi/models/tan.py", "src/avoi/datasets/common.py", "src/avoi/datasets/iam.py",
    "src/avoi/datasets/ait_episodes.py", "src/avoi/datasets/cert.py", "src/avoi/evaluation/engine.py",
    "src/avoi/evaluation/stage2.py", "src/avoi/evaluation/labels.py", "src/avoi/baselines/llm_planner.py",
    "testbed/scenarios/generator.py", "testbed/oracle.py", "testbed/evidence_collectors/collectors.py", "experiments/run_stage2.py",
    "experiments/run_llm_planner_stage2.py",
]
DATA_GLOBS = ["data/processed/iam_stage2/evidence_store/*.json", "data/processed/iam_stage2/ground_truth/*.json",
              "data/processed/ait_stage2/evidence_store.json", "data/processed/ait_stage2/ground_truth/episode_labels.csv",
              "data/processed/cert_stage2/evidence_store.json", "data/processed/cert_stage2/ground_truth/episode_labels.csv",
              "data/processed/iam/evidence_store/*.json", "data/processed/ait/evidence_store.json", "data/processed/cert/evidence_store.json"]


def hashes() -> dict:
    files = {f: sha256_file(ROOT / f) for f in FROZEN_FILES}
    data = {}
    for g in DATA_GLOBS:
        base, pat = g.rsplit("/", 1)
        paths = sorted((ROOT / base).glob(pat))
        h = hashlib.sha256()
        for p in paths:
            h.update(p.name.encode()); h.update(sha256_file(p).encode())
        data[g] = {"n_files": len(paths), "sha256": h.hexdigest()}
    return {"files": files, "data": data,
            "combined_sha256": hashlib.sha256(json.dumps({"files": files, "data": data}, sort_keys=True).encode()).hexdigest()}


def verify() -> dict:
    fr = json.loads(FREEZE.read_text(encoding="utf-8"))
    now = hashes()
    changed = [f for f, h in fr["hashes"]["files"].items() if now["files"].get(f) != h]
    changed += [g for g, h in fr["hashes"]["data"].items() if now["data"].get(g) != h]
    if changed:
        raise SystemExit(f"Stage-2 frozen protocol changed: {changed}")
    return fr


def run_parallel(phase: str, workers: int):
    from avoi.evaluation.stage2 import run_domain_objective
    res = []
    log = S2 / f"{phase}_log.jsonl"
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_domain_objective, {"domain": d, "objective": o, "phase": phase}): (d, o) for d, o in TASKS}
        for fut in as_completed(futs):
            d, o = futs[fut]
            try:
                r = fut.result(); r["status_task"] = "ok"
            except Exception as exc:
                import traceback
                r = {"domain": d, "objective": o, "phase": phase, "status_task": "failed", "error": repr(exc), "traceback": traceback.format_exc()}
            res.append(r)
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(r) + "\n")
            print(phase, d, o, r["status_task"], r.get("status"), r.get("seconds"), flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["freeze", "adequacy", "confirm"])
    ap.add_argument("--workers", type=int, default=9)
    args = ap.parse_args()
    S2.mkdir(parents=True, exist_ok=True)
    if args.phase == "freeze":
        if FREEZE.exists():
            raise SystemExit("Stage-2 freeze exists; create a versioned corrected freeze instead of overwriting.")
        import yaml
        rec = {"frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "statement": "Stage-2 protocol frozen before any Stage-2 adequacy validation or confirmation evaluation.",
               "stage1_freeze_sha256": json.loads((ROOT / "results/stage1_ungated/EXPERIMENT_FREEZE.json").read_text())["hashes"]["combined_sha256"],
               "stage1_git_commit": "7bb325ceff9629709642ce9f6cf85039002f2eac",
               "adequacy_policy": yaml.safe_load((ROOT / "config/model_adequacy.yaml").read_text(encoding="utf-8")),
               "stage2_protocol": yaml.safe_load((ROOT / "config/stage2.yaml").read_text(encoding="utf-8")),
               "loss_matrix": yaml.safe_load((ROOT / "config/loss_matrix.yaml").read_text(encoding="utf-8")),
               "hyperparameters": yaml.safe_load((ROOT / "config/hyperparameters.yaml").read_text(encoding="utf-8")),
               "iam_generation_seed": yaml.safe_load((ROOT / "config/scenario_generator_stage2.yaml").read_text(encoding="utf-8"))["master_seed"],
               "required_figures": ["model_adequacy_diagnostics", "calibration_curve", "roc_pr_curves", "risk_coverage_raw",
                                    "risk_coverage_adequacy_enforced", "cost_safety_frontier", "budget_performance_curve",
                                    "acquisition_risk_trajectory", "evidence_request_ecdf", "missingness_robustness", "missingness_uar_coverage",
                                    "privacy_safety_tradeoff", "action_frequency_heatmap", "asymmetric_loss_ablation", "adequacy_sensitivity",
                                    "cost_violin", "decision_flow"],
               "required_tables": ["table_model_adequacy", "adequacy_gate_effect", "main_comparison_raw", "main_comparison_enforced",
                                   "matched_coverage", "matched_safety_nondegenerate", "budget", "missingness", "privacy", "ablation",
                                   "asymmetric_loss_ablation", "escalation", "zero_acquisition", "statistics", "adequacy_sensitivity",
                                   "fa_sensitivity", "table_boundary", "llm_planner", "main_comparison_validated_models"],
               "analysis_code_note": ("Table/figure/report code (stage2_tables.py, stage2_figures.py, run_stage2_report.py) is not hashed "
                                      "so presentation bugs can be fixed; it reads only saved raw outputs and cannot change them."),
               "hashes": hashes()}
        FREEZE.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
        print("Stage-2 freeze:", rec["hashes"]["combined_sha256"], "freeze-file sha256:", sha256_file(FREEZE))
    elif args.phase == "adequacy":
        fr = verify()
        if DECISIONS.exists():
            raise SystemExit("Adequacy decisions already frozen.")
        res = run_parallel("adequacy", args.workers)
        if any(r["status_task"] != "ok" for r in res):
            raise SystemExit("adequacy tasks failed; see results/stage2/adequacy_log.jsonl")
        decisions = {}
        for d, o in TASKS:
            rec = json.loads((S2 / "adequacy" / f"{d}_{o}.json").read_text(encoding="utf-8"))
            decisions[f"{d}|{o}"] = rec["decision"]
        body = {"frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "stage2_freeze_sha256": fr["hashes"]["combined_sha256"], "decisions": decisions}
        body["decisions_sha256"] = hashlib.sha256(json.dumps(decisions, sort_keys=True, default=float).encode()).hexdigest()
        DECISIONS.write_text(json.dumps(body, indent=1, default=float), encoding="utf-8")
        print("adequacy decisions frozen:", body["decisions_sha256"])
    else:
        verify()
        dec = json.loads(DECISIONS.read_text(encoding="utf-8"))
        chk = hashlib.sha256(json.dumps(dec["decisions"], sort_keys=True, default=float).encode()).hexdigest()
        if chk != dec["decisions_sha256"]:
            raise SystemExit("adequacy decisions modified after freezing")
        res = run_parallel("confirm", args.workers)
        print("failed:", sum(r["status_task"] != "ok" for r in res))
