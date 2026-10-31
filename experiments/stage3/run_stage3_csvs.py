"""Export Stage-3 analysis results to CSV files from saved raw outputs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "stage3"))

import pandas as pd  # noqa: E402

from run_stage3 import WP1_OBJECTIVES, WP2_AIT_CLAIMS, WP2_CERT_CLAIM  # noqa: E402

from avoi.evaluation import stage3_tables as T3  # noqa: E402

S3 = T3.S3


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def build_all():
    T3.TABLES.mkdir(parents=True, exist_ok=True)
    out = {}

    # ---------------- WP1
    adapt_summary = load_json(S3 / "confirmation" / "wp1" / "adaptivity_summary.json")
    fh_rows = pd.read_csv(S3 / "raw" / "wp1" / "fixed_horizon_rows.csv.gz") if (S3 / "raw" / "wp1" / "fixed_horizon_rows.csv.gz").exists() else None
    rows_raw_wp1 = pd.read_csv(S3 / "raw" / "wp1" / "normal_operation_raw.csv.gz") if (S3 / "raw" / "wp1" / "normal_operation_raw.csv.gz").exists() else None
    rows_enf_wp1 = pd.read_csv(S3 / "raw" / "wp1" / "normal_operation_enforced.csv.gz") if (S3 / "raw" / "wp1" / "normal_operation_enforced.csv.gz").exists() else None
    if adapt_summary is not None:
        out["adaptive_selection"] = T3.write(T3.table_adaptive_selection(adapt_summary, WP1_OBJECTIVES), "table_adaptive_selection_stage3",
                                             "Stage 3 WP1. Direct evidence of adaptive next-evidence selection (confirmation partition)")
    if fh_rows is not None:
        fh_table = T3.table_fixed_horizon(fh_rows, WP1_OBJECTIVES)
        out["fixed_horizon"] = T3.write(fh_table, "table_fixed_horizon_stage3", "Stage 3 WP1. Adaptive vs Frozen-Order AVOI, fixed evidence horizons k=2,3")
    if rows_raw_wp1 is not None and rows_enf_wp1 is not None:
        out["normal_operation"] = T3.write(T3.table_normal_operation(rows_raw_wp1, rows_enf_wp1, WP1_OBJECTIVES), "table_normal_operation_stage3",
                                           "Stage 3 WP1. Normal-operation comparison (validation-tuned thresholds, raw and adequacy-enforced)")

    # ---------------- WP2 AIT
    ait_records = {c: load_json(S3 / "validation" / f"wp2_ait_{c}.json") for c in WP2_AIT_CLAIMS}
    ait_records = {k: v for k, v in ait_records.items() if v is not None}
    cert_record = load_json(S3 / "validation" / "wp2_cert.json")

    if ait_records or cert_record:
        out["external_adequacy"] = T3.write(T3.table_external_adequacy(ait_records, cert_record), "table_external_adequacy_stage3",
                                            "Stage 3 WP2. External-domain (AIT, CERT) evidence-model adequacy (unchanged Stage-2 policy)")
        out["zero_shot_vs_target"] = T3.write(T3.table_zero_shot_vs_target(ait_records, cert_record), "table_zero_shot_vs_target_stage3",
                                              "Stage 3 WP2. Zero-shot vs target-calibrated external evidence models")
    stability = T3.table_feature_stability(S3 / "development")
    if not stability.empty:
        out["feature_stability"] = T3.write(stability, "table_feature_stability_stage3", "Stage 3 WP2. Development-only feature-stability diagnostic")

    def load_ext_raw(p: Path):
        if not p.exists():
            return None
        df = pd.read_csv(p)
        df["method_family"] = df["method"].str.replace(r"\[s\d+\]", "", regex=True)   # Stage-2 per_method() convention
        return df

    ait_raw = load_ext_raw(S3 / "raw" / "wp2_ait" / "episodes_raw.csv.gz")
    cert_raw = load_ext_raw(S3 / "raw" / "wp2_cert" / "episodes_raw.csv.gz")
    ext_avoi = []
    validated_claims = []
    for claim in WP2_AIT_CLAIMS:
        if ait_raw is not None and claim in ait_records and ait_records[claim]["decision"]["status"] == "VALIDATED":
            validated_claims.append(("ait", claim))
    if cert_raw is not None and cert_record and cert_record["decision"]["status"] == "VALIDATED":
        validated_claims.append(("cert", WP2_CERT_CLAIM))
    for dom, claim in validated_claims:
        raw = ait_raw if dom == "ait" else cert_raw
        t = T3.table_external_avoi(raw, dom, claim)
        t.insert(2, "note", "VALIDATED - primary E2 evidence")
        ext_avoi.append(t)
    # also include RESTRICTED/UNSUPPORTED claims as diagnostic-only rows (protocol Section 45: never discard them)
    for dom, claim, rec, raw in [("ait", c, ait_records.get(c), ait_raw) for c in WP2_AIT_CLAIMS] + [("cert", WP2_CERT_CLAIM, cert_record, cert_raw)]:
        if rec is None or raw is None or (dom, claim) in validated_claims:
            continue
        t = T3.table_external_avoi(raw, dom, claim)
        t.insert(2, "note", f"DIAGNOSTIC ONLY - status {rec['decision']['status']}, not VALIDATED (E2 not applicable)")
        ext_avoi.append(t)
    if ext_avoi:
        out["external_avoi"] = T3.write(pd.concat(ext_avoi, ignore_index=True), "table_external_avoi_stage3",
                                        "Stage 3 WP2. AVOI vs baselines on external evidence models (VALIDATED = primary E2 evidence; others diagnostic only, protocol Section 45)")

    print(f"Wrote {len(out)} Stage-3 CSV result tables")
    return out


if __name__ == "__main__":
    build_all()
