"""Sensitivity and generalisation experiments: false-assurance loss, cost/privacy weights, leave-one-family-out (IAM).
(Missingness, reliability degradation and action-cost change are produced inside the primary experiment; threshold
grids are produced by the curve outputs; prevalence shift is computed by run_statistics.py from episode records.)"""
import argparse

from common import run_tasks, tasks_for, verify_freeze

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiments", default="loss_sensitivity,weight_sensitivity,lofo")
    ap.add_argument("--domains", default="iam,ait,cert")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    verify_freeze()
    for exp in args.experiments.split(","):
        doms = ["iam"] if exp == "lofo" else args.domains.split(",")
        run_tasks(tasks_for(exp, doms), args.workers, log_name=exp)
