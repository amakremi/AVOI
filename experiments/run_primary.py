"""Layer A primary nested validation on the controlled IAM testbed (primary, regime A, calibrated-logistic model)."""
import argparse

from common import run_tasks, tasks_for, verify_freeze

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiments", default="primary,regime_a,model_lr")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    verify_freeze()
    for exp in args.experiments.split(","):
        run_tasks(tasks_for(exp, ["iam"]), args.workers, log_name=f"{exp}_iam")
