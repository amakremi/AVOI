"""CSV-ready supplementary analysis tables derived from saved experiment outputs."""
from __future__ import annotations

import numpy as np
import pandas as pd

from avoi.evaluation import analysis_data as AD
from avoi.evaluation import metrics as MT
from avoi.evaluation import stats_tables as ST

BASELINES = ["B0-AllEvidence", "B1-FixedChecklist", "B2-Random", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI",
             "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI", "B7b-Lookahead2VOI"]

# Supplementary result tables

def ablation_table(domains) -> pd.DataFrame:
    t, _ = ST.main_table(domains, "ablation", AD.ABLATIONS, name="t7", caption="")
    return t[~t["dataset"].str.startswith("macro")] if not t.empty else t


def generalization_table(domains, main_store) -> pd.DataFrame:
    rows = []
    for dom in domains:
        df = AD.tuned("primary", dom)
        for obj, g in df.groupby("objective"):
            a = AD.per_method(g, "AVOI-GRC")
            if a.empty:
                continue
            sa = MT.decision_metrics(a)
            best, best_loss = None, np.inf
            for b in BASELINES:
                x = AD.per_method(g, b)
                if x.empty:
                    continue
                lb = float(x["loss"].mean())
                if lb < best_loss:
                    best, best_loss = b, lb
            sb = MT.decision_metrics(AD.per_method(g, best))
            rows.append({"dataset": dom, "objective_or_claim": obj, "setting": "primary (cold, regime B, TAN)", "n": sa["n"],
                         "violated_prevalence": sa["prevalence_violated"], "AVOI_expected_loss": sa["expected_loss"],
                         "AVOI_UAR": sa["UAR"], "AVOI_acquisitions": sa["mean_acquisitions"], "AVOI_coverage": sa["coverage"],
                         "lowest_loss_baseline": best, "baseline_expected_loss": sb["expected_loss"], "baseline_UAR": sb["UAR"],
                         "baseline_acquisitions": sb["mean_acquisitions"]})
        for exp, label in (("regime_a", "cost regime A (uniform)"), ("model_lr", "calibrated logistic evidence model")):
            d2 = AD.tuned(exp, dom)
            if d2.empty:
                continue
            a = AD.per_method(d2, "AVOI-GRC")
            sa = MT.decision_metrics(a)
            cands = {b: float(AD.per_method(d2, b)["loss"].mean()) for b in BASELINES if not AD.per_method(d2, b).empty}
            best = min(cands, key=cands.get)
            sb = MT.decision_metrics(AD.per_method(d2, best))
            rows.append({"dataset": dom, "objective_or_claim": "all", "setting": label, "n": sa["n"],
                         "violated_prevalence": sa["prevalence_violated"], "AVOI_expected_loss": sa["expected_loss"], "AVOI_UAR": sa["UAR"],
                         "AVOI_acquisitions": sa["mean_acquisitions"], "AVOI_coverage": sa["coverage"], "lowest_loss_baseline": best,
                         "baseline_expected_loss": sb["expected_loss"], "baseline_UAR": sb["UAR"], "baseline_acquisitions": sb["mean_acquisitions"]})
    lofo = AD.tuned("lofo", "iam")
    if not lofo.empty:
        a = MT.decision_metrics(AD.per_method(lofo, "AVOI-GRC"))
        cands = {b: float(AD.per_method(lofo, b)["loss"].mean()) for b in BASELINES if not AD.per_method(lofo, b).empty}
        best = min(cands, key=cands.get)
        sb = MT.decision_metrics(AD.per_method(lofo, best))
        rows.append({"dataset": "iam", "objective_or_claim": "all", "setting": "leave-one-scenario-family-out (40 folds)", "n": a["n"],
                     "violated_prevalence": a["prevalence_violated"], "AVOI_expected_loss": a["expected_loss"], "AVOI_UAR": a["UAR"],
                     "AVOI_acquisitions": a["mean_acquisitions"], "AVOI_coverage": a["coverage"], "lowest_loss_baseline": best,
                     "baseline_expected_loss": sb["expected_loss"], "baseline_UAR": sb["UAR"], "baseline_acquisitions": sb["mean_acquisitions"]})
    for dom in domains:  # prevalence shift by importance reweighting of held-out episodes (no retraining)
        df = AD.tuned("primary", dom)
        for prev in (0.1, 0.25, 0.5):
            for m in ("AVOI-GRC", "B1-FixedChecklist", "B4-InformationGain", "B5-GenericVOI", "B6-ConfidenceThreshold"):
                x = AD.per_method(df, m)
                p0 = (x["y"] == 0).mean()
                if p0 in (0, 1):
                    continue
                w = np.where(x["y"] == 0, prev / p0, (1 - prev) / (1 - p0))
                rows.append({"dataset": dom, "objective_or_claim": "all", "setting": f"prevalence reweighted to {prev:.0%} violated",
                             "n": len(x), "violated_prevalence": prev, "method": m,
                             "AVOI_expected_loss" if m == "AVOI-GRC" else "baseline_expected_loss": float(np.average(x["loss"], weights=w)),
                             "lowest_loss_baseline": m if m != "AVOI-GRC" else ""})
    return pd.DataFrame(rows)


def sensitivity_table(domains) -> pd.DataFrame:
    rows = []
    meths = ("AVOI-GRC", "B1-FixedChecklist", "B4-InformationGain", "B5-GenericVOI", "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI")
    for dom in domains:
        ls = AD.episodes("loss_sensitivity", dom)
        if not ls.empty:
            ls = ls[(ls["start"] == "cold") & (ls["shift"] == "none")]
            for (cond, m), g in ls.groupby(["condition", "method"]):
                s = MT.decision_metrics(g)
                rows.append({"dataset": dom, "factor": "false-assurance penalty", "level": cond.split("|")[0], "method": m,
                             "expected_loss": s["expected_loss"], "UAR": s["UAR"], "coverage": s["coverage"],
                             "acquisitions": s["mean_acquisitions"], "cost": s["normalized_cost"], "privacy": s["privacy_exposure"]})
        ws = AD.episodes("weight_sensitivity", dom)
        if not ws.empty:
            ws = ws[(ws["start"] == "cold") & (ws["shift"] == "none")]
            for cond, g in ws.groupby("condition"):
                s = MT.decision_metrics(g)
                parts = dict(p.split("=") for p in cond.split("|"))
                factor = "cost weight λ multiplier" if parts["mu"] == "1.0" else "privacy weight μ multiplier"
                rows.append({"dataset": dom, "factor": factor, "level": parts["lam"] if factor.startswith("cost") else parts["mu"],
                             "method": "AVOI-GRC", "expected_loss": s["expected_loss"], "UAR": s["UAR"], "coverage": s["coverage"],
                             "acquisitions": s["mean_acquisitions"], "cost": s["normalized_cost"], "privacy": s["privacy_exposure"]})
        prim = AD.episodes("primary", dom)
        prim = prim[prim["condition"] == AD.PRIMARY_COND]
        for (m, mode, level), g in prim[prim["shift"] == "none"].groupby(["method", "missing_mode", "missing_level"]):
            if m in meths:
                s = MT.decision_metrics(g)
                rows.append({"dataset": dom, "factor": "initial missingness", "level": f"{mode}:{int(level * 100)}%", "method": m,
                             "expected_loss": s["expected_loss"], "UAR": s["UAR"], "coverage": s["coverage"],
                             "acquisitions": s["mean_acquisitions"], "cost": s["normalized_cost"], "privacy": s["privacy_exposure"]})
        cold_all = prim[(prim["shift"] == "none") & (prim["start"] == "cold")]
        for (m, sh), g in prim[prim["shift"].str.startswith(("degrade", "cost:"))].groupby(["method", "shift"]):
            s = MT.decision_metrics(g)
            base = cold_all[(cold_all["method"] == m) & cold_all["episode_id"].isin(set(g["episode_id"]))]
            rows.append({"dataset": dom, "factor": "reliability degradation" if sh.startswith("degrade") else "action-cost change",
                         "level": sh, "method": m, "expected_loss": s["expected_loss"], "UAR": s["UAR"], "coverage": s["coverage"],
                         "acquisitions": s["mean_acquisitions"], "cost": s["normalized_cost"], "privacy": s["privacy_exposure"],
                         "n_episodes": s["n"], "cold_expected_loss_same_episodes": float(base["loss"].mean()) if len(base) else np.nan,
                         "cold_acquisitions_same_episodes": float(base["n_acq"].mean()) if len(base) else np.nan})
        cur = AD.curves("primary", dom)
        if not cur.empty:
            c = AD.pooled_curve(cur, "AVOI-GRC")
            for tau in (0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0):
                r = c[np.isclose(c["tau"].astype(float), tau)]
                if not r.empty:
                    r = r.iloc[0]
                    rows.append({"dataset": dom, "factor": "risk threshold τ (held-out grid)", "level": f"{tau:.2f}", "method": "AVOI-GRC",
                                 "expected_loss": r["expected_loss"], "UAR": r["UAR"], "coverage": r["coverage"],
                                 "acquisitions": r["acquisitions"], "cost": r["cost"], "privacy": r["privacy"]})
    return pd.DataFrame(rows)


