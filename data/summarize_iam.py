"""Data summary for the controlled IAM testbed (label prevalence, conflict subset, setup warnings)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from avoi.datasets.iam import load_iam  # noqa: E402
from avoi.evaluation.labels import load_labels  # noqa: E402

logs = [json.loads(line) for line in (ROOT / "data/processed/iam/collection_log.jsonl").read_text().splitlines()]
print("scenario records", len(logs), "with setup warnings", sum(1 for r in logs if r.get("setup_log")))
for k, d in load_iam().items():
    y = load_labels("iam", d.episode_ids)
    print(f"{k:24s} n={d.n} satisfied={y.mean():.3f} conflict_subset={int(d.strata['conflict'].sum())}")
