"""Layer B public telemetry replay (AIT-LDS v2.0, CERT r4.2): primary, regime A, calibrated-logistic model."""
import argparse

from common import run_tasks, tasks_for, verify_freeze

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiments", default="primary,regime_a,model_lr")
    ap.add_argument("--domains", default="ait,cert")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    verify_freeze()
    for exp in args.experiments.split(","):
        run_tasks(tasks_for(exp, args.domains.split(",")), args.workers, log_name=f"{exp}_public")
