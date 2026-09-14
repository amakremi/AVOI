"""Mandatory ablation study (all domains)."""
import argparse

from common import run_tasks, tasks_for, verify_freeze

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", default="iam,ait,cert")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    verify_freeze()
    run_tasks(tasks_for("ablation", args.domains.split(",")), args.workers, log_name="ablation")
