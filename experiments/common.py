"""Shared experiment utilities: frozen-configuration verification and parallel task execution."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
FREEZE = ROOT / "results" / "EXPERIMENT_FREEZE.json"

FROZEN_FILES = [
    "config/assurance_objectives.yaml", "config/evidence_actions.yaml", "config/loss_matrix.yaml",
    "config/hyperparameters.yaml", "config/experiments.yaml", "config/scenario_generator.yaml",
    "docs/PREREGISTERED_HYPOTHESES.md", "data/DATASET_MANIFEST.json", "data/manifests/dataset_sources.json",
    "testbed/scenarios/generator.py", "testbed/keycloak/applier.py", "testbed/keycloak/kc.py",
    "testbed/evidence_collectors/collectors.py", "testbed/oracle.py",
    "src/avoi/agent.py", "src/avoi/avoi.py", "src/avoi/bayes_risk.py", "src/avoi/costs.py", "src/avoi/actions.py",
    "src/avoi/models/tan.py", "src/avoi/models/discriminative.py", "src/avoi/datasets/common.py",
    "src/avoi/datasets/iam.py", "src/avoi/datasets/ait.py", "src/avoi/datasets/ait_episodes.py", "src/avoi/datasets/cert.py",
    "src/avoi/evaluation/engine.py", "src/avoi/evaluation/runner.py", "src/avoi/evaluation/labels.py",
    "src/avoi/privacy.py", "src/avoi/baselines/llm_planner.py", "experiments/common.py",
]
FROZEN_DATA_GLOBS = ["data/processed/iam/evidence_store/*.json", "data/processed/iam/ground_truth/*.json",
                     "data/processed/ait/evidence_store.json", "data/processed/ait/ground_truth/episode_labels.csv",
                     "data/processed/cert/evidence_store.json", "data/processed/cert/ground_truth/episode_labels.csv"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_hashes() -> dict:
    files = {f: sha256_file(ROOT / f) for f in FROZEN_FILES}
    data = {}
    for g in FROZEN_DATA_GLOBS:
        base, pattern = g.rsplit("/", 1)
        paths = sorted((ROOT / base).glob(pattern))
        h = hashlib.sha256()
        for p in paths:
            h.update(p.name.encode())
            h.update(sha256_file(p).encode())
        data[g] = {"n_files": len(paths), "sha256": h.hexdigest()}
    combined = hashlib.sha256(json.dumps({"files": files, "data": data}, sort_keys=True).encode()).hexdigest()
    return {"files": files, "data": data, "combined_sha256": combined}


def verify_freeze() -> dict:
    if not FREEZE.exists():
        raise SystemExit("results/EXPERIMENT_FREEZE.json missing: run experiments/freeze_experiment.py first")
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    now = compute_hashes()
    changed = [f for f in frozen["hashes"]["files"] if frozen["hashes"]["files"][f] != now["files"].get(f)]
    changed += [g for g in frozen["hashes"]["data"] if frozen["hashes"]["data"][g] != now["data"].get(g)]
    if changed:
        raise SystemExit(f"Frozen experimental configuration changed: {changed}. Refusing to run.")
    return frozen


def run_tasks(tasks: list[dict], workers: int | None = None, log_name: str = "run") -> list[dict]:
    from avoi.evaluation.runner import run_task
    workers = workers or max(1, min(len(tasks), (os.cpu_count() or 4) - 4))
    log = ROOT / "results" / "raw" / f"{log_name}_log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    results = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_task, t): t for t in tasks}
        for k, fut in enumerate(as_completed(futs), 1):
            t = futs[fut]
            try:
                r = fut.result()
                r["status"] = "ok"
            except Exception as exc:  # recorded, never silently dropped
                import traceback
                r = {**t, "status": "failed", "error": repr(exc), "traceback": traceback.format_exc()}
            results.append(r)
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(r) + "\n")
            print(f"[{k}/{len(tasks)}] {r.get('experiment')} {r.get('domain')} {r.get('objective')} f{r.get('fold')} "
                  f"{r['status']} {r.get('seconds', '')}s elapsed={time.time() - t0:.0f}s", flush=True)
    return results


def tasks_for(experiment: str, domains: list[str]) -> list[dict]:
    from avoi.evaluation.runner import load_domain, cfg_all
    exp_cfg = cfg_all()["exp"]["experiments"][experiment]
    out = []
    for dom in domains:
        objs, _ = load_domain(dom)
        n_folds = {"iam": 5, "ait": 2, "cert": 5}[dom]
        if exp_cfg.get("outer") == "lofo":
            n_folds = len(set(next(iter(objs.values())).groups))
        for oid in objs:
            for f in range(n_folds):
                out.append({"experiment": experiment, "domain": dom, "objective": oid, "fold": f})
    return out
