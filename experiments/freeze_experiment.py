"""Freeze datasets, testbed, objectives, scenario generator, labels, actions, costs, losses, grids, metrics, primary plots
and hypotheses by writing SHA-256 hashes to results/EXPERIMENT_FREEZE.json. Must run BEFORE final experiments."""
from __future__ import annotations

import datetime as dt
import json

from common import FREEZE, ROOT, compute_hashes

if __name__ == "__main__":
    if FREEZE.exists():
        raise SystemExit("EXPERIMENT_FREEZE.json already exists; refusing to overwrite a freeze.")
    hashes = compute_hashes()
    record = {
        "frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "statement": "Configuration frozen before final experiments. Runners verify these hashes and refuse to run on change.",
        "included_domains": ["iam (Layer A)", "ait (Layer B)", "cert (Layer B)"],
        "excluded_domains": {"botsv3": "official answer key only via e-mail request to Splunk; data in proprietary Splunk index "
                                        "format requiring Splunk Enterprise licence acceptance",
                             "lanl_cyber1": "download gated by LANL e-mail form (not bypassed)"},
        "primary_metrics": ["UAR", "FAR_A", "expected decision loss", "mean/median acquisitions", "normalised cost",
                            "privacy exposure", "escalation rate", "autonomous coverage", "balanced accuracy", "macro F1",
                            "MCC", "AUROC", "AUPRC", "Brier", "log loss", "ECE", "calibration slope/intercept"],
        "hashes": hashes,
    }
    FREEZE.parent.mkdir(parents=True, exist_ok=True)
    FREEZE.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print("frozen:", hashes["combined_sha256"])
