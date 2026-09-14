"""Write environment_report.txt, results/SEED_MANIFEST.json and results/EXPERIMENT_MANIFEST.json."""
from __future__ import annotations

import datetime as dt
import json
import os
import platform
import subprocess
import sys
from importlib import metadata

import yaml

from common import ROOT


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60, shell=isinstance(cmd, str)).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"unavailable ({exc!r})"


if __name__ == "__main__":
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    cpu = run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"]) if os.name == "nt" else run("lscpu | head -20")
    ram = run(["powershell", "-NoProfile", "-Command", "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)"]) if os.name == "nt" else run("free -g")
    lines = [
        f"generated_utc: {now}",
        f"python: {sys.version}",
        f"platform: {platform.platform()} ({platform.system()} {platform.release()} {platform.version()})",
        f"cpu: {cpu}", f"logical_cpus: {os.cpu_count()}", f"ram_gb: {ram}",
        f"gpu: {run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'])}",
        f"docker: {run(['docker', '--version'])}", f"docker_compose: {run(['docker', 'compose', 'version'])}",
        f"ollama: {run(['ollama', '--version'])}",
        f"git_commit: {run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']) or 'no commit'}",
        "", "python packages:",
    ]
    lines += sorted(f"  {d.metadata['Name']}=={d.version}" for d in metadata.distributions())
    logs = sorted((ROOT / "results" / "raw").glob("*_log.jsonl"))
    lines += ["", "experiment task logs (execution timestamps = file modification times, UTC):"]
    for p in logs:
        lines.append(f"  {p.name}: {dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat(timespec='seconds')}")
    (ROOT / "environment_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    hp = yaml.safe_load((ROOT / "config" / "hyperparameters.yaml").read_text(encoding="utf-8"))
    gen = yaml.safe_load((ROOT / "config" / "scenario_generator.yaml").read_text(encoding="utf-8"))
    seeds = {
        "master_seed": hp["master_seed"],
        "scenario_generator_master_seed": gen["master_seed"],
        "scenario_seed_rule": "sha256('{master_seed}|scenario|{index}')[:8] little-endian (testbed/scenarios/generator.py)",
        "family_seed_rule": "sha256('{master_seed}|family|{family_id}')[:8]",
        "cross_validation": "StratifiedGroupKFold/GroupKFold random_state = master_seed",
        "random_baseline_seeds": list(range(hp["random_baseline_seeds"])),
        "random_order_rule": "sha256('{seed}|{episode_id}')[:8]",
        "initial_availability_rule": "stable_seed(master_seed, mode, level, episode_id)",
        "degradation_rule": "stable_seed(master_seed, 'degrade', source_type, episode_id)",
        "cert_sampling_seed": 20260914, "bootstrap_seed": 20260914, "llm_seed": 0, "llm_temperature": 0,
        "mfa_login_test_sample_rule": "sha256(realm|mfa-sample) ordering (testbed/evidence_collectors/collectors.py)",
    }
    (ROOT / "results" / "SEED_MANIFEST.json").write_text(json.dumps(seeds, indent=1), encoding="utf-8")
    tasks = []
    for p in logs:
        for line in p.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            tasks.append({k: r.get(k) for k in ("experiment", "domain", "objective", "fold", "status", "seconds", "n_rows")})
    freeze = json.loads((ROOT / "results" / "EXPERIMENT_FREEZE.json").read_text(encoding="utf-8"))
    manifest = {"generated_utc": now, "frozen_configuration_sha256": freeze["hashes"]["combined_sha256"],
                "experiments": yaml.safe_load((ROOT / "config" / "experiments.yaml").read_text(encoding="utf-8"))["experiments"],
                "n_tasks": len(tasks), "n_failed": sum(t["status"] != "ok" for t in tasks), "tasks": tasks,
                "llm_planner": json.loads((ROOT / "results" / "raw" / "llm_planner" / "run_info.json").read_text())
                if (ROOT / "results" / "raw" / "llm_planner" / "run_info.json").exists() else None}
    (ROOT / "results" / "EXPERIMENT_MANIFEST.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("tasks", len(tasks), "failed", manifest["n_failed"])
