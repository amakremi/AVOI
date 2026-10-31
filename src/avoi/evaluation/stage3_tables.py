"""Stage-3 tables (WP1 adaptivity, WP2 external adequacy/AVOI). Reuses Stage-2 statistics/table-writer infrastructure."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from avoi import adequacy as AQ
from avoi.evaluation import metrics as MT
from avoi.evaluation import stage2_analysis as SA
from avoi.evaluation import stage2_tables as T2
from avoi.evaluation import stats_tables as ST

ROOT = Path(__file__).resolve().parents[3]
S3 = ROOT / "results" / "stage3"
TABLES = S3 / "tables"
DISPLAY = dict(T2.DISPLAY, **{"Frozen-Order AVOI": "Frozen-Order AVOI"})


def write(df, name, caption):
    ST.TABLES = TABLES
    ST.write_table(df, name, caption)
    return {"name": name, "csv": f"results/stage3/tables/{name}.csv"}


def ci_str(est, lo, hi, d=3):
    return T2.ci_str(est, lo, hi, d)


def boot_summary(x, n_boot=5000, seed=20270401):
    return T2.boot_summary(x, n_boot, seed)


def boot_diff(a, b, metric, n_boot=5000, seed=20270401):
    return T2.boot_diff(a, b, metric, n_boot, seed)


# ====================================================================================== WP1 adaptive selection
def table_adaptive_selection(adapt_summary: dict, wp1_objectives: list[str]) -> pd.DataFrame:
    rows = []
    for oid in wp1_objectives:
        s = adapt_summary[oid]
        a, fzn, perm = s["adaptive"], s["frozen"], s["permutation"]
        rows.append({"objective": oid, "adequacy_status": s["adequacy_status"],
                     "distinct_actions_step1": a["distinct_actions_by_step"].get("1", a["distinct_actions_by_step"].get(1)),
                     "distinct_actions_step2": a["distinct_actions_by_step"].get("2", a["distinct_actions_by_step"].get(2)),
                     "mean_action_entropy_bits_(t>=2)": a["mean_action_entropy_bits_t_ge_2"],
                     "ranking_change_rate": a["ranking_change_rate"], "rank_reversal_rate": a["rank_reversal_rate"],
                     "history_action_permutation_p": perm["p"], "permutation_statistic_MI_nats": perm["statistic_conditional_MI_nats"],
                     "permutation_n_steps": perm["n_steps"], "permutation_n_blocks": perm["n_blocks"]})
    df = pd.DataFrame(rows)
    df["permutation_p_holm"] = MT.holm(df["history_action_permutation_p"].tolist())
    return df


def table_fixed_horizon(fh_rows: pd.DataFrame, wp1_objectives: list[str]) -> pd.DataFrame:
    rows = []
    for oid in wp1_objectives:
        d = fh_rows[fh_rows["objective"] == oid]
        for k in sorted(d["horizon"].unique()):
            dk = d[d["horizon"] == k]
            a = dk[dk["method"] == "AVOI"]
            f = dk[dk["method"] == "Frozen-Order AVOI"]
            keys = ["episode_id", "y", "group"]
            m = a.merge(f, on=keys, suffixes=("_a", "_f"))
            diff = (m["loss_a"] - m["loss_f"]).to_numpy(float)
            groups = m["group"].to_numpy()
            # paired group bootstrap on the mean difference
            ug = np.unique(groups)
            idx_by = {g: np.flatnonzero(groups == g) for g in ug}
            rng = np.random.default_rng(20270402)
            boots = []
            for _ in range(5000):
                pick = rng.choice(ug, size=len(ug), replace=True)
                sel = np.concatenate([idx_by[g] for g in pick])
                boots.append(diff[sel].mean())
            lo, hi = np.quantile(boots, [0.025, 0.975])
            sf = MT.signflip_permutation(m["loss_a"].to_numpy(float), m["loss_f"].to_numpy(float), n_perm=10000, seed=20270402)
            rows.append({"objective": oid, "horizon_k": int(k), "adaptive_loss": float(a["loss"].mean()), "frozen_loss": float(f["loss"].mean()),
                        "difference": float(diff.mean()), "ci_low": float(lo), "ci_high": float(hi), "n_pairs": len(m),
                        "signflip_p": sf["p"], "adaptive_lower": bool(hi < 0)})
    df = pd.DataFrame(rows)
    df["signflip_p_holm"] = MT.holm(df["signflip_p"].tolist())
    return df


def table_normal_operation(rows_raw: pd.DataFrame, rows_enf: pd.DataFrame, wp1_objectives: list[str]) -> pd.DataFrame:
    out = []
    for mode, df in (("raw", rows_raw), ("enforced", rows_enf)):
        for oid in wp1_objectives:
            d = df[df["objective"] == oid]
            for m in d["method"].unique():
                x = T2.per_method(d, m) if m == "B2-Random" else d[d["method"] == m]
                if x.empty:
                    continue
                r = T2.method_row(x, m, {"adequacy_mode": mode, "objective": oid})
                out.append(r)
    return T2.strip(out)


def table_zero_shot_vs_target(ait_records: dict, cert_record: dict | None) -> pd.DataFrame:
    rows = []
    recs = {("ait", k): v for k, v in ait_records.items()}
    if cert_record is not None:
        recs[("cert", cert_record["objective"])] = cert_record
    for (dom, claim), r in recs.items():
        for variant in ("zero_shot", "target_calibrated"):
            m = r[variant]["metrics"]
            ci = r[variant]["bootstrap"]["ci"]
            rows.append({"domain": dom, "objective": claim, "variant": variant, "AUROC": ci_str(m["AUROC"], *ci["AUROC"]),
                        "PR_skill": ci_str(m["PR_skill"], *ci["PR_skill"]), "BSS": ci_str(m["BSS"], *ci["BSS"]),
                        "ECE": ci_str(m["ECE"], *ci["ECE"]), "calibration_slope": ci_str(m["calibration_slope"], *ci["calibration_slope"]),
                        "n_violated": m["n_violated"], "n_satisfied": m["n_satisfied"]})
    return pd.DataFrame(rows)


def table_feature_stability(dev_dir: Path) -> pd.DataFrame:
    parts = []
    for f in sorted(dev_dir.glob("*_feature_stability.csv")):
        d = pd.read_csv(f)
        d.insert(0, "source", f.stem.replace("_feature_stability", ""))
        parts.append(d)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def table_external_adequacy(ait_records: dict, cert_record: dict | None) -> pd.DataFrame:
    rows = []
    recs = [("ait", k, v) for k, v in ait_records.items()]
    if cert_record is not None:
        recs.append(("cert", cert_record["objective"], cert_record))
    for dom, claim, r in recs:
        m = r["target_calibrated"]["metrics"]; ci = r["target_calibrated"]["bootstrap"]["ci"]
        dec = r["decision"]
        rows.append({"domain": dom, "objective": claim, "model": r["selection"]["chosen_model"]["kind"], "alpha": r["selection"]["chosen_model"].get("alpha"),
                     "development_datasets": ", ".join(r.get("development_sources", r.get("development_releases", []))),
                     "target_adaptation": "target-calibrated (primary)", "calibrator": r["selection"]["calibrator"],
                     "adequacy_validation_N": m["n"], "violations": m["n_violated"], "independent_groups": r["target_calibrated"]["bootstrap"]["n_groups"],
                     "AUROC": ci_str(m["AUROC"], *ci["AUROC"]), "AUPRC": ci_str(m["AUPRC"], *ci["AUPRC"]), "PR_skill": ci_str(m["PR_skill"], *ci["PR_skill"]),
                     "Brier": round(m["Brier"], 4), "BSS": ci_str(m["BSS"], *ci["BSS"]), "ECE": ci_str(m["ECE"], *ci["ECE"]),
                     "calibration_slope": ci_str(m["calibration_slope"], *ci["calibration_slope"]),
                     "adequacy_status": dec["status"], "reason": dec["reason"]})
    return pd.DataFrame(rows)


def table_external_avoi(raw: pd.DataFrame, domain: str, claim: str) -> pd.DataFrame:
    d = raw[(raw["domain"] == domain) & (raw["objective"] == claim) & (raw["experiment"] == "primary")]
    rows = []
    for m in T2.METHODS:
        x = T2.per_method(d, m)
        if x.empty:
            continue
        rows.append(T2.method_row(x, m, {"domain": domain, "objective": claim}))
    return T2.strip(rows)
