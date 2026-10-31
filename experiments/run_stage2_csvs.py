"""Export Stage-2 analysis results to CSV files from saved raw outputs."""
from __future__ import annotations

import sys

from common import ROOT

sys.path.insert(0, str(ROOT / "experiments"))
from run_stage2 import verify  # noqa: E402

from avoi.evaluation import stage2_tables as T  # noqa: E402


if __name__ == "__main__":
    verify()
    outputs = T.build_all()
    print(f"Wrote {len(outputs)} Stage-2 CSV result tables")
