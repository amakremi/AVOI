"""POST-HOC analyses (declared as deviations from the pre-registration in RESULTS.md).

Deviation D1 — degenerate safety-target matching. The pre-registered safety-target operating point ("lowest inner cost
with inner UAR <= target") is satisfied trivially by thresholds that stop immediately and decide NotAssured for every
episode (UAR = 0 at zero cost, because UAR does not penalise false non-assurance). The pre-registered H1 and Table 5 are
reported as registered; this module adds a non-degenerate variant: lowest inner cost among thresholds with inner
UAR <= target AND inner tuning objective J <= 1.0 (J of escalating every episode = 1.0 + 0 terms), i.e. operating points
that are at least as good as not automating at all. Held-out per-episode results at the selected thresholds are
recomputed exactly from the saved full trajectories (results/traces) with the same truncation used by the runner.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import yaml

from avoi.agent import truncate
from avoi.bayes_risk import LossMatrix
from avoi.evaluation import analysis_data as AD
from avoi.evaluation import engine as E
from avoi.evaluation import metrics as MT

TRACED = ["AVOI-GRC", "B0-AllEvidence", "B1-FixedChecklist", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI",
          "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI", "B7b-Lookahead2VOI"]


def specs() -> dict:
    lcfg = yaml.safe_load((AD.ROOT / "config" / "loss_matrix.yaml").read_text(encoding="utf-8"))
    w = lcfg["preference_weights"]
    return {s.name: s for s in E.method_suite(LossMatrix(), w["lambda_cost"], w["mu_privacy"], w["nu_delay"], 1e-3, 0)}


def select_nondegenerate(tuning: pd.DataFrame, method: str, target: float) -> dict:
    """(objective, fold) -> tau ('none' for threshold-free methods); units without a qualifying threshold are absent."""
    t = tuning[(tuning["method"] == method) & (tuning["condition"] == AD.PRIMARY_COND)].copy()
    t["tau_key"] = t["tau"].astype(float).fillna(-1.0)
    J = t[t["inner_J"].notna()][["objective", "fold", "tau_key", "inner_J"]]
    S = t[t["inner_uar"].notna()][["objective", "fold", "tau_key", "tau", "inner_uar", "inner_cost", "inner_coverage"]]
    m = S.merge(J, on=["objective", "fold", "tau_key"])
    out = {}
    for (obj, fold), g in m.groupby(["objective", "fold"]):
        ok = g[(g["inner_uar"] <= target) & (g["inner_J"] <= 1.0)].sort_values(["inner_cost", "inner_coverage"], ascending=[True, False])
        if not ok.empty:
            out[(obj, int(fold))] = "none" if ok.iloc[0]["tau_key"] == -1.0 else float(ok.iloc[0]["tau"])
    return out

def episodes_at(domain: str, method: str, choice: dict) -> pd.DataFrame:
    sp = specs()[method]
    L = LossMatrix()
    rows = []
    for tr in AD.load_traces(domain, method):
        key = (tr["objective_id"], int(tr.get("fold", -1)))
        rows.append((tr, key))
    # traces do not store the fold: recover from the episode tables
    prim = AD.tuned("primary", domain)
    fold_of = prim[prim["method"] == method].set_index(["objective", "episode_id"])["fold"].to_dict()
    out = []
    for tr, _ in rows:
        fold = fold_of.get((tr["objective_id"], tr["episode_id"]))
        tau = choice.get((tr["objective_id"], fold))
        if tau is None:
            continue
        op = truncate(tr, sp.cfg, None if tau == "none" else tau)
        out.append({"objective": tr["objective_id"], "fold": fold, "episode_id": tr["episode_id"], "y": tr["y"],
                    "decision": op["decision"], "belief": op["belief"], "n_acq": op["n_acquisitions"], "cost": op["cost"],
                    "delay": op["delay"], "seconds": op["seconds"], "privacy": len(op["privacy_categories"]) / 10,
                    "loss": L.realized_loss(op["decision"], tr["y"]), "tau": tau})
    return pd.DataFrame(out)


def safety_table_nondegenerate(domains) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, h1 = [], []
    for dom in domains:
        tuning = AD.table("primary", dom, "tuning")
        n_units = AD.tuned("primary", dom)[["objective", "fold"]].drop_duplicates().shape[0]
        cache = {}
        for target in (0.01, 0.02, 0.05):
            for m in TRACED:
                ch = select_nondegenerate(tuning, m, target)
                ach = sum(v is not None for v in ch.values())
                ep = episodes_at(dom, m, ch)
                cache[(m, target)] = ep
                if ep.empty:
                    rows.append({"dataset": dom, "method": m, "target": f"UAR<={target} & inner J<=1", "status": "not achieved",
                                 "units_achieved": f"{ach}/{n_units}"})
                    continue
                s = MT.decision_metrics(ep)
                ci = MT.bootstrap_ci(ep, ["UAR", "normalized_cost", "mean_acquisitions", "coverage"], seed=7)
                rows.append({"dataset": dom, "method": m, "target": f"UAR<={target} & inner J<=1",
                             "status": ("achieved" if ach == n_units else f"partially achieved ({ach}/{n_units} objective-folds)") +
                                       ("; held-out UAR meets target" if s["UAR"] <= target else "; held-out UAR exceeds target"),
                             "units_achieved": f"{ach}/{n_units}", "UAR": f"{s['UAR']:.4f} [{ci['UAR'][0]:.4f}, {ci['UAR'][1]:.4f}]",
                             "coverage": f"{s['coverage']:.3f}", "mean_acquisitions": f"{s['mean_acquisitions']:.3f}",
                             "normalized_cost": f"{s['normalized_cost']:.4f}", "expected_loss": f"{s['expected_loss']:.4f}", "n_episodes": s["n"]})
            a, b = cache[("AVOI-GRC", target)], cache[("B1-FixedChecklist", target)]
            if a.empty or b.empty:
                h1.append({"dataset": dom, "target": target, "result": "not testable (target not achieved)"})
                continue
            p = a.merge(b, on=["objective", "fold", "episode_id", "y"], suffixes=("_a", "_b"))
            w = MT.wilcoxon_paired(p["n_acq_a"], p["n_acq_b"])
            d, lo, hi = MT.paired_bootstrap_diff(p["n_acq_a"].to_numpy(float), p["n_acq_b"].to_numpy(float), p["y"].to_numpy(), seed=7)
            viol = (p["y"] == 0).to_numpy(float)
            du, ulo, uhi = MT.paired_bootstrap_diff(((p["decision_a"] == "Assured") & (p["y"] == 0)).to_numpy(float),
                                                    ((p["decision_b"] == "Assured") & (p["y"] == 0)).to_numpy(float), p["y"].to_numpy(), seed=7, denom=viol)
            h1.append({"dataset": dom, "target": target, "n_pairs": len(p), "mean_acq_AVOI": p["n_acq_a"].mean(), "mean_acq_B1": p["n_acq_b"].mean(),
                       "acq_diff": d, "acq_ci_low": lo, "acq_ci_high": hi, "wilcoxon_p": w["p"], "rank_biserial": w["effect_rank_biserial"],
                       "uar_diff": du, "uar_ci_low": ulo, "uar_ci_high": uhi})
        hdf = pd.DataFrame([r for r in h1 if r["dataset"] == dom and "wilcoxon_p" in r])
        if not hdf.empty:
            adj = MT.holm(hdf["wilcoxon_p"].tolist())
            for r, pa in zip([r for r in h1 if r["dataset"] == dom and "wilcoxon_p" in r], adj):
                r["p_holm"] = pa
                r["verdict_posthoc"] = "supported" if (pa < 0.05 and r["acq_ci_high"] < 0 and r["uar_ci_high"] <= 0.02) else "not supported"
                if r["mean_acq_AVOI"] == 0 and r["mean_acq_B1"] == 0:
                    r["verdict_posthoc"] = "not testable - still degenerate (both methods acquire no evidence at the selected thresholds)"
    return pd.DataFrame(rows), pd.DataFrame(h1)


def budget_filled(domain: str) -> pd.DataFrame:
    """Budget results with budgets above an objective's action count carried forward (budget >= m is unconstrained)."""
    bud = AD.table("primary", domain, "budget")
    bud = bud[bud["condition"] == AD.PRIMARY_COND]
    out = [bud]
    kmax = int(bud["budget"].max())
    for obj, g in bud.groupby("objective"):
        m = int(g["budget"].max())
        last = g[g["budget"] == m]
        for k in range(m + 1, kmax + 1):
            out.append(last.assign(budget=k))
    return pd.concat(out, ignore_index=True)
