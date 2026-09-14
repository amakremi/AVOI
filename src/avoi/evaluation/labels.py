"""RESTRICTED label access. Only evaluation code may import this module (enforced by tests/test_leakage.py).

Ground truth is loaded from data/processed/<domain>/ground_truth and aligned to episode ids. Labels are used to
(1) fit evidence models on TRAINING folds, (2) score held-out decisions. They are never passed to policies,
environments or evidence collectors.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]


def load_labels(domain: str, episode_ids: np.ndarray) -> np.ndarray:
    gt = ROOT / "data" / "processed" / domain / "ground_truth"
    if domain == "iam":
        cache = {}
        y = np.zeros(len(episode_ids), dtype=int)
        for k, eid in enumerate(episode_ids):
            scn, obj = str(eid).split("|")
            if scn not in cache:
                cache[scn] = json.loads((gt / f"{scn}.json").read_text(encoding="utf-8"))["labels"]
            y[k] = int(cache[scn][obj])
        return y
    table = {}
    with (gt / "episode_labels.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            table[r["episode_id"]] = int(r["y"])
    return np.array([table[str(e)] for e in episode_ids], dtype=int)
