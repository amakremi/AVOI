"""Export analysis results as CSV files from saved experiment outputs."""
from __future__ import annotations

import json

import pandas as pd

from common import ROOT, verify_freeze
from avoi.evaluation import analysis_data as AD
from avoi.evaluation import analysis_tables as AT
from avoi.evaluation import metrics as MT
from avoi.evaluation import stats_tables as ST


def save(df: pd.DataFrame, name: str) -> None:
    ST.write_table(df, name)


def llm_planner_table() -> pd.DataFrame:
    path = ROOT / "results" / "raw" / "llm_planner" / "episodes_llm_planner.csv.gz"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    rows = []
    for method, group in df.groupby("method"):
        metrics = MT.decision_metrics(group)
        ci = MT.bootstrap_ci(group, ["UAR", "expected_loss", "mean_acquisitions", "coverage"], seed=1)
        rows.append({
            "method": method,
            "n": metrics["n"],
            "UAR": ST.ci_str(metrics["UAR"], *ci["UAR"]),
            "expected_loss": ST.ci_str(metrics["expected_loss"], *ci["expected_loss"]),
            "mean_acquisitions": ST.ci_str(metrics["mean_acquisitions"], *ci["mean_acquisitions"]),
            "coverage": ST.ci_str(metrics["coverage"], *ci["coverage"]),
            "normalized_cost": metrics["normalized_cost"],
        })
    info_path = ROOT / "results" / "raw" / "llm_planner" / "run_info.json"
    info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
    out = pd.DataFrame(rows)
    out["model"] = info.get("model", "unknown")
    out["invalid_responses"] = info.get("invalid_responses", "unknown")
    return out


def main() -> None:
    verify_freeze()
    domains = [domain for domain in AD.DOMAINS if not AD.episodes("primary", domain).empty]
    tables = []

    for name, frame in (
        ("table1_dataset_provenance", ST.provenance_table()),
        ("table2_objectives_actions", ST.objectives_table()),
        ("table4_matched_coverage", ST.target_table(domains, "coverage")),
        ("table5_matched_safety", ST.target_table(domains, "uar")),
        ("table6_calibration", ST.calibration_table(domains)),
    ):
        save(frame, name)
        tables.append(name)

    main_table, store = ST.main_table(domains)
    save(main_table, "table3_main_comparison")
    tables.append("table3_main_comparison")
    save(AT.ablation_table(domains), "table7_ablation")
    tables.append("table7_ablation")

    paired = pd.concat([ST.paired_stats(domain) for domain in domains], ignore_index=True)
    ablation_paired = pd.concat([
        ST.paired_stats(domain, "ablation", [method for method in AD.ABLATIONS if method != "AVOI-GRC"])
        for domain in domains
    ], ignore_index=True)
    friedman = pd.DataFrame([{"dataset": domain, **ST.friedman_table(domain)} for domain in domains])
    paired_cols = ["dataset", "comparison", "metric", "test", "statistic", "p", "p_holm"]
    paired_cols += [column for column in paired.columns if column.startswith("effect")]
    paired_cols += ["mean_difference", "ci_low", "ci_high", "n_pairs"]
    for name, frame in (
        ("table8_statistical_significance", paired[paired_cols]),
        ("table8b_ablation_significance", ablation_paired),
        ("table8c_friedman_omnibus", friedman),
        ("table9_generalization", AT.generalization_table(domains, store)),
        ("table10_sensitivity", AT.sensitivity_table(domains)),
    ):
        save(frame, name)
        tables.append(name)

    from avoi.evaluation import posthoc as PH

    nondegenerate, posthoc = PH.safety_table_nondegenerate(domains)
    for name, frame in (
        ("table5b_matched_safety_nondegenerate", nondegenerate),
        ("table11b_h1_posthoc", posthoc),
        ("table11_hypotheses", ST.evaluate_hypotheses(domains)),
    ):
        save(frame, name)
        tables.append(name)

    llm = llm_planner_table()
    if not llm.empty:
        save(llm, "table12_llm_planner")
        tables.append("table12_llm_planner")

    print(f"Wrote {len(tables)} CSV result tables to results/tables")


if __name__ == "__main__":
    main()
