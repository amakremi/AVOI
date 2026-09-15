"""Archive the completed Stage-1 (ungated) experiment into results/stage1_ungated/ with a SHA-256 manifest.

Copies (never moves) raw episode outputs, traces, tables, figures, reports, freeze/seed/experiment manifests,
configuration, pre-registration, environment report and the Stage-1 LLM-planner (llama3.1:8b) outputs.
Refuses to overwrite an existing archive. Stage-1 numbers are historical and must not be edited.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "results" / "stage1_ungated"

COPY = {
    "results/raw": "raw", "results/traces": "traces", "results/tables": "tables", "results/figures": "figures",
    "results/final_report": "final_report", "results/EXPERIMENT_FREEZE.json": "EXPERIMENT_FREEZE.json",
    "results/SEED_MANIFEST.json": "SEED_MANIFEST.json", "results/EXPERIMENT_MANIFEST.json": "EXPERIMENT_MANIFEST.json",
    "config": "config", "docs/PREREGISTERED_HYPOTHESES.md": "docs/PREREGISTERED_HYPOTHESES.md",
    "environment_report.txt": "environment_report.txt", "requirements.lock.txt": "requirements.lock.txt",
    "data/DATASET_MANIFEST.json": "data/DATASET_MANIFEST.json", "results/archive/llm_planner_llama3.1_8b": "llm_planner_llama3.1_8b",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    if (DEST / "MANIFEST.json").exists():
        raise SystemExit("Stage-1 archive already exists; refusing to overwrite.")
    DEST.mkdir(parents=True, exist_ok=True)
    for src, dst in COPY.items():
        s, d = ROOT / src, DEST / dst
        if not s.exists():
            print("missing (skipped):", src)
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)
    files = []
    for p in sorted(DEST.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.json":
            st = p.stat()
            files.append({"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p), "bytes": st.st_size,
                          "modified_utc": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat(timespec="seconds")})
    freeze = json.loads((DEST / "EXPERIMENT_FREEZE.json").read_text(encoding="utf-8"))
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    manifest = {"stage": "Stage 1 - original ungated AVOI experiment (historical; do not edit)",
                "archived_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "original_freeze_combined_sha256": freeze["hashes"]["combined_sha256"],
                "original_freeze_utc": freeze["frozen_utc"], "git_commit_at_archive": commit,
                "note": "Method displayed as 'AVOI-GRC' in these historical artefacts; manuscript-facing relabelled copies "
                        "(label change only) are in results/stage1_ungated/manuscript/.",
                "n_files": len(files), "files": files}
    (DEST / "MANIFEST.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("archived", len(files), "files; freeze", freeze["hashes"]["combined_sha256"][:16], "commit", commit[:7])
