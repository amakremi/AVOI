"""Pre-Stage-3 snapshot: SHA-256 manifest of every Stage-1/2 result artefact (refuses to overwrite).

  python experiments/stage3/archive_snapshot.py          -> results/archive/pre_stage3_snapshot/MANIFEST.json
  python experiments/stage3/archive_snapshot.py verify   -> exit 1 if any archived artefact changed
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "results" / "archive" / "pre_stage3_snapshot"
TREES = ["results/stage1_ungated", "results/stage2", "results/final_report_v2"]
COPIES = ["results/stage2/EXPERIMENT_FREEZE_STAGE2.json", "results/stage2/ADEQUACY_DECISIONS.json",
          "results/stage1_ungated/EXPERIMENT_FREEZE.json", "config/model_adequacy.yaml", "config/stage2.yaml",
          "config/loss_matrix.yaml", "config/hyperparameters.yaml", "config/assurance_objectives.yaml",
          "config/evidence_actions.yaml", "config/scenario_generator.yaml", "config/scenario_generator_stage2.yaml"]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def files() -> list[Path]:
    out = []
    for t in TREES:
        out += sorted(p for p in (ROOT / t).rglob("*") if p.is_file())
    return out


def build():
    if (SNAP / "MANIFEST.json").exists():
        raise SystemExit("pre-Stage-3 snapshot exists; refusing to overwrite")
    SNAP.mkdir(parents=True, exist_ok=True)
    for c in COPIES:
        dst = SNAP / "copies" / c
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / c, dst)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = {"created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "git_commit": commit,
           "git_commits": {"stage1": "7bb325ceff9629709642ce9f6cf85039002f2eac", "stage2_freeze": "5679e9e", "stage2_decisions": "3ffaad3",
                           "stage2_results": commit},
           "stage1_freeze_sha256": json.loads((ROOT / "results/stage1_ungated/EXPERIMENT_FREEZE.json").read_text())["hashes"]["combined_sha256"],
           "stage2_freeze_sha256": json.loads((ROOT / "results/stage2/EXPERIMENT_FREEZE_STAGE2.json").read_text())["hashes"]["combined_sha256"],
           "stage2_decisions_sha256": json.loads((ROOT / "results/stage2/ADEQUACY_DECISIONS.json").read_text())["decisions_sha256"],
           "model_adequacy_yaml_sha256": sha(ROOT / "config/model_adequacy.yaml"),
           "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in files()]}
    (SNAP / "MANIFEST.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(len(rec["files"]), "files; commit", commit)


def verify() -> list[str]:
    rec = json.loads((SNAP / "MANIFEST.json").read_text(encoding="utf-8"))
    bad = [f["path"] for f in rec["files"] if not (ROOT / f["path"]).exists() or sha(ROOT / f["path"]) != f["sha256"]]
    listed = {f["path"] for f in rec["files"]}
    added = [p.relative_to(ROOT).as_posix() for p in files() if p.relative_to(ROOT).as_posix() not in listed]
    return bad + [f"ADDED:{a}" for a in added]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        changed = verify()
        print("unchanged" if not changed else changed[:50])
        sys.exit(1 if changed else 0)
    build()
