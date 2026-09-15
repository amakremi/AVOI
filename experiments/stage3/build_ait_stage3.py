"""Stage 3: index the untouched AIT-LDS v2.0 testbeds (shaw, wheeler, wilson) and build their episode store.

Reuses avoi.datasets.ait.index and avoi.datasets.ait_episodes.build unchanged. Prints only row counts and timings - no
label summaries (wheeler and wilson are confirmation data).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from avoi.datasets import ait, ait_episodes  # noqa: E402

TESTBEDS = ["shaw", "wheeler", "wilson"]

if __name__ == "__main__":
    for tb in TESTBEDS:
        if (ait.OUT / f"{tb}_index_meta.json").exists():
            print(tb, "index present (reused)", flush=True)
            continue
        info = ait.index(tb)
        print(tb, "rows", info["rows"], "seconds", info["index_seconds"], flush=True)
    ait_episodes.build(TESTBEDS, ait.OUT.parent / "ait_stage3")
    print("episode store written to data/processed/ait_stage3", flush=True)
