"""Stage-2 tables, statistics and hypothesis evaluation (all values computed from results/stage2 raw outputs)."""
from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats as sps

from avoi import adequacy as AQ
from avoi.bayes_risk import HUMAN_REVIEW, LossMatrix
from avoi.evaluation import metrics as MT
from avoi.evaluation import stage2_analysis as SA
from avoi.evaluation import stats_tables as ST

ROOT = Path(__file__).resolve().parents[3]
S2 = ROOT / "results" / "stage2"
TABLES = S2 / "tables"
DOMAINS = ["iam", "ait", "cert"]
DOM_LABEL = {"iam": "Controlled IAM", "ait": "AIT-LDS v2.0", "cert": "CERT (r4.2 dev / r5.2 confirmation)"}
PRIMARY_COND = "fa=10.0|lam=0.05|mu=0.02|nu=0.02"
METHODS = ["B0-AllEvidence", "B1-FixedChecklist", "B2-Random", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI",
           "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI", "B7b-Lookahead2VOI", "AVOI"]
DISPLAY = {"B0-AllEvidence": "All Evidence", "B1-FixedChecklist": "Checklist", "B2-Random": "Random (20 seeds)",
           "B3-CheapestFirst": "Cheapest First", "B4-InformationGain": "Information Gain", "B5-GenericVOI": "Generic VOI",
           "B6-ConfidenceThreshold": "Confidence Threshold", "B7-MyopicCostSensitiveVOI": "Myopic Cost-Sensitive VOI",
           "B7b-Lookahead2VOI": "Lookahead-2", "AVOI": "AVOI", "A1-NoAsymmetricLoss": "AVOI - asymmetric loss (symmetric 2:2)",
           "A2-NoLearnedReliability": "AVOI - learned reliability", "A3-NoCost": "AVOI - acquisition cost", "A4-NoPrivacy": "AVOI - privacy",
           "A5-NoDelay": "AVOI - delay", "A6-NoEscalation": "AVOI - HumanReview/abstention", "A7-EntropyInsteadOfRisk": "AVOI with entropy reduction",
           "A8-NaiveBayesModel": "AVOI with Naive Bayes evidence model"}
N_BOOT = 5000
LOSS = LossMatrix()


def write(df, name, caption):
    ST.TABLES = TABLES
    ST.write_table(df, name, caption)
    return {"name": name, **{ext: f"results/stage2/tables/{name}.{ext}" for ext in ("csv", "md", "tex")}}


# ====================================================================================== loading
@lru_cache(maxsize=None)
def episodes(mode: str) -> pd.DataFrame:
    files = sorted((S2 / "raw" / mode).glob("episodes_*.csv.gz"))
    df = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)
    df["method_family"] = df["method"].str.replace(r"\[s\d+\]", "", regex=True)
    df["group"] = df["domain"] + ":" + df["group"].astype(str)   # bootstrap groups never collide across domains
    return df


@lru_cache(maxsize=None)
def aux(kind: str, mode: str = "raw") -> pd.DataFrame:
    files = sorted((S2 / "raw" / mode).glob(f"{kind}_*.csv.gz")) if kind != "tuning" else sorted((S2 / "raw" / "tuning").glob("tuning_*.csv.gz"))
    return pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True) if files else pd.DataFrame()


@lru_cache(maxsize=None)
def adequacy_records() -> dict:
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted((S2 / "adequacy").glob("*.json"))}


@lru_cache(maxsize=None)
def decisions() -> dict:
    return json.loads((S2 / "ADEQUACY_DECISIONS.json").read_text(encoding="utf-8"))["decisions"]


def status_of(domain, objective):
    return decisions()[f"{domain}|{objective}"]["status"]


def cold(df, experiment="primary", condition=PRIMARY_COND):
    return df[(df["experiment"] == experiment) & (df["condition"] == condition) & (df["start"] == "cold") & (df["shift"] == "none")]


def per_method(df, method):
    if method != "B2-Random":
        return df[df["method"] == method].copy()
    r = df[df["method_family"] == "B2-Random"].copy()
    r["assured_f"] = (r["decision"] == "Assured").astype(float)
    r["notassured_f"] = (r["decision"] == "NotAssured").astype(float)
    r["hr_f"] = (r["decision"] == HUMAN_REVIEW).astype(float)
    g = r.groupby(["domain", "objective", "episode_id", "group", "y"], as_index=False).agg(
        belief=("belief", "mean"), loss=("loss", "mean"), n_acq=("n_acq", "mean"), cost=("cost", "mean"), privacy=("privacy", "mean"),
        delay=("delay", "mean"), assured_f=("assured_f", "mean"), notassured_f=("notassured_f", "mean"), hr_f=("hr_f", "mean"))
    g["method"] = "B2-Random"
    g["decision"] = "mixed"
    return g


# ====================================================================================== group bootstrap (vectorised)
def _indicators(x: pd.DataFrame) -> pd.DataFrame:
    if "assured_f" not in x:
        x = x.assign(assured_f=(x["decision"] == "Assured").astype(float), notassured_f=(x["decision"] == "NotAssured").astype(float),
                     hr_f=(x["decision"] == HUMAN_REVIEW).astype(float))
    v = (x["y"] == 0).astype(float)
    b = x["belief"].astype(float)
    return pd.DataFrame({"group": x["group"].astype(str), "n": 1.0, "viol": v, "unsafe": x["assured_f"] * v, "assured": x["assured_f"],
                         "auto": 1 - x["hr_f"], "hr": x["hr_f"], "loss": x["loss"], "nacq": x["n_acq"], "cost": x["cost"], "privacy": x["privacy"],
                         "tp": ((b < 0.5) & (x["y"] == 0)).astype(float), "tn": ((b >= 0.5) & (x["y"] == 1)).astype(float),
                         "sat": (x["y"] == 1).astype(float)})


def _div(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(b > 0, a / np.where(b > 0, b, 1), np.nan)
    return float(r) if r.ndim == 0 else r


def _metrics_from_sums(S: dict) -> dict:
    return {"UAR": _div(S["unsafe"], S["viol"]), "FAA": _div(S["unsafe"], S["assured"]), "coverage": _div(S["auto"], S["n"]),
            "human_review_rate": _div(S["hr"], S["n"]), "expected_loss": _div(S["loss"], S["n"]), "mean_acquisitions": _div(S["nacq"], S["n"]),
            "normalized_cost": _div(S["cost"], S["n"]), "privacy_exposure": _div(S["privacy"], S["n"]),
            "balanced_accuracy": 0.5 * (_div(S["tp"], S["viol"]) + _div(S["tn"], S["sat"]))}


def boot_summary(x: pd.DataFrame, n_boot: int = N_BOOT, seed: int = 20261103) -> dict:
    ind = _indicators(x)
    G = ind.groupby("group").sum(numeric_only=True)
    point = _metrics_from_sums({c: float(G[c].sum()) for c in G.columns})
    rng = np.random.default_rng(seed)
    W = rng.multinomial(len(G), np.full(len(G), 1 / len(G)), size=n_boot)   # group resampling counts
    sums = {c: W @ G[c].to_numpy() for c in G.columns}
    bs = _metrics_from_sums(sums)
    ci = {k: (float(np.nanquantile(v, 0.025)), float(np.nanquantile(v, 0.975))) for k, v in bs.items()}
    return {"point": {k: float(v) for k, v in point.items()}, "ci": ci, "n": int(len(x)), "n_groups": int(len(G))}


def boot_diff(a: pd.DataFrame, b: pd.DataFrame, metric: str, n_boot: int = N_BOOT, seed: int = 20261103) -> tuple[float, float, float]:
    keys = ["objective", "episode_id", "y", "group"]
    m = a[keys].merge(b[keys], on=keys)
    ia = _indicators(a.merge(m, on=keys)).groupby("group").sum(numeric_only=True)
    ib = _indicators(b.merge(m, on=keys)).groupby("group").sum(numeric_only=True)
    ib = ib.reindex(ia.index)
    rng = np.random.default_rng(seed)
    W = rng.multinomial(len(ia), np.full(len(ia), 1 / len(ia)), size=n_boot)
    pa = _metrics_from_sums({c: float(ia[c].sum()) for c in ia.columns})[metric]
    pb = _metrics_from_sums({c: float(ib[c].sum()) for c in ib.columns})[metric]
    da = _metrics_from_sums({c: W @ ia[c].to_numpy() for c in ia.columns})[metric]
    db = _metrics_from_sums({c: W @ ib[c].to_numpy() for c in ib.columns})[metric]
    d = da - db
    return float(pa - pb), float(np.nanquantile(d, 0.025)), float(np.nanquantile(d, 0.975))


def ci_str(p, lo, hi, d=3):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "n/a"
    return f"{p:.{d}f} [{lo:.{d}f}, {hi:.{d}f}]"


def method_row(x: pd.DataFrame, name: str, extra: dict) -> dict:
    s = boot_summary(x)
    P, C = s["point"], s["ci"]
    if name != "B2-Random":
        dm = MT.decision_metrics(x.assign(seconds=x.get("seconds", 0), delay=x.get("delay", 0)))
        mcc, med = dm["MCC"], float(x["n_acq"].median())
    else:
        mcc, med = np.nan, float(x["n_acq"].median())
    return {**extra, "method": DISPLAY.get(name, name), "n_episodes": s["n"], "n_groups": s["n_groups"],
            "autonomous_coverage": ci_str(P["coverage"], *C["coverage"]), "UAR": ci_str(P["UAR"], *C["UAR"]),
            "false_assurance_among_assurances": ci_str(P["FAA"], *C["FAA"]), "expected_loss": ci_str(P["expected_loss"], *C["expected_loss"]),
            "balanced_accuracy": ci_str(P["balanced_accuracy"], *C["balanced_accuracy"]), "MCC": mcc,
            "mean_acquisitions": ci_str(P["mean_acquisitions"], *C["mean_acquisitions"]), "median_acquisitions": med,
            "normalized_cost": ci_str(P["normalized_cost"], *C["normalized_cost"], 4), "privacy_exposure": ci_str(P["privacy_exposure"], *C["privacy_exposure"]),
            "human_review_rate": ci_str(P["human_review_rate"], *C["human_review_rate"]), "_point": P, "_ci": C}


def strip(rows):
    return pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])


# ====================================================================================== tables
def table_model_adequacy() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, pre = [], []
    for key, r in adequacy_records().items():
        dec = r["decision"]
        m, ci = r["validation_primary"]["metrics"], r["validation_primary"]["bootstrap"]["ci"]
        sel = r["selection"]
        rows.append({"domain": r["domain"], "objective": r["objective"],
                     "evidence_model": f"{sel['selected_model']['kind'].upper()} (alpha={sel['selected_model']['alpha']})",
                     "calibration_method": sel["selected_calibrator"], "prevalence_violated": m["prevalence_violated"],
                     "violated_cases": m["n_violated"], "independent_groups": r["validation_primary"]["bootstrap"]["n_groups"],
                     "groups_with_violation": r["groups_with_violation"],
                     "AUROC": ci_str(m["AUROC"], *ci["AUROC"]), "AUPRC": ci_str(m["AUPRC"], *ci["AUPRC"]),
                     "PR_skill": ci_str(m["PR_skill"], *ci["PR_skill"]), "MCC": ci_str(m["MCC"], *ci["MCC"]),
                     "Brier": ci_str(m["Brier"], *ci["Brier"]), "BSS": ci_str(m["BSS"], *ci["BSS"]), "ECE": ci_str(m["ECE"], *ci["ECE"]),
                     "calibration_slope": ci_str(m["calibration_slope"], *ci["calibration_slope"]),
                     "calibration_intercept": ci_str(m["calibration_intercept"], *ci["calibration_intercept"]),
                     "discrimination_pass": dec["discrimination_pass"], "calibration_pass": dec["calibration_pass"],
                     "sample_support_pass": dec["support_pass"], "adequacy_status": dec["status"], "reason": dec["reason"]})
        mu = r["validation_uncalibrated"]["metrics"]
        oofu, oofc = sel["oof_metrics_uncalibrated"], sel["oof_metrics_calibrated"]
        pre.append({"domain": r["domain"], "objective": r["objective"], "calibrator": sel["selected_calibrator"],
                    "calibrator_cv_log_loss": json.dumps({k: round(v, 4) for k, v in sel["calibrator_cv_log_loss"].items()}),
                    "dev_oof_ECE_before": oofu["ECE"], "dev_oof_ECE_after": oofc["ECE"], "dev_oof_slope_before": oofu["calibration_slope"],
                    "dev_oof_slope_after": oofc["calibration_slope"], "validation_ECE_uncalibrated": mu["ECE"], "validation_ECE_calibrated": m["ECE"],
                    "validation_BSS_uncalibrated": mu["BSS"], "validation_BSS_calibrated": m["BSS"],
                    "validation_slope_uncalibrated": mu["calibration_slope"], "validation_slope_calibrated": m["calibration_slope"],
                    "validation_AUROC_uncalibrated": mu["AUROC"], "validation_AUROC_calibrated": m["AUROC"],
                    "masked_state_ECE_calibrated": r["masked_diagnostic_metrics"]["ECE"], "masked_state_AUROC_calibrated": r["masked_diagnostic_metrics"]["AUROC"]})
    return pd.DataFrame(rows), pd.DataFrame(pre)


def main_tables(raw: pd.DataFrame, enf: pd.DataFrame) -> dict:
    out = {}
    for label, df, subset in (("raw_all_models", raw, None), ("enforced_all_models", enf, None), ("raw_validated_models", raw, "validated")):
        rows = []
        for dom in DOMAINS:
            d = cold(df[df["domain"] == dom])
            if subset == "validated":
                ok = [o for o in d["objective"].unique() if status_of(dom, o) == AQ.VALIDATED]
                d = d[d["objective"].isin(ok)]
            if d.empty:
                rows.append({"domain": DOM_LABEL[dom], "method": "(no VALIDATED evidence model)" if subset else "(no data)"})
                continue
            for mth in METHODS:
                x = per_method(d, mth)
                if not x.empty:
                    rows.append(method_row(x, mth, {"domain": DOM_LABEL[dom], "adequacy_mode": "enforced" if "enforced" in label else "raw (ungated)",
                                                    "models": ", ".join(sorted(d["objective"].unique()))}))
        out[label] = rows
    return out


def gate_effect(raw, enf) -> pd.DataFrame:
    rows = []
    for dom in DOMAINS:
        for level in ("domain",) + tuple(sorted(raw[raw["domain"] == dom]["objective"].unique())):
            r = cold(raw[(raw["domain"] == dom) & (raw["method"] == "AVOI")])
            e = cold(enf[(enf["domain"] == dom) & (enf["method"] == "AVOI")])
            if level != "domain":
                r, e = r[r["objective"] == level], e[e["objective"] == level]
                st = status_of(dom, level)
            else:
                sts = sorted({status_of(dom, o) for o in r["objective"].unique()})
                st = "/".join(sts)
            if r.empty:
                continue
            br, be = boot_summary(r), boot_summary(e)
            rows.append({"domain": DOM_LABEL[dom], "scope": level, "adequacy_status": st,
                         "raw_AVOI_UAR": ci_str(br["point"]["UAR"], *br["ci"]["UAR"]), "gated_AVOI_UAR": ci_str(be["point"]["UAR"], *be["ci"]["UAR"]),
                         "raw_FAA": ci_str(br["point"]["FAA"], *br["ci"]["FAA"]), "gated_FAA": ci_str(be["point"]["FAA"], *be["ci"]["FAA"]),
                         "raw_coverage": ci_str(br["point"]["coverage"], *br["ci"]["coverage"]),
                         "gated_coverage": ci_str(be["point"]["coverage"], *be["ci"]["coverage"]),
                         "raw_expected_loss": ci_str(br["point"]["expected_loss"], *br["ci"]["expected_loss"]),
                         "gated_expected_loss": ci_str(be["point"]["expected_loss"], *be["ci"]["expected_loss"]),
                         "raw_human_review_rate": br["point"]["human_review_rate"], "gated_human_review_rate": be["point"]["human_review_rate"],
                         "interpretation": ("gate inactive (VALIDATED)" if st == AQ.VALIDATED else
                                            "autonomy withheld: any UAR reduction is caused by abstention, not by better acquisition")})
    return pd.DataFrame(rows)


def boundary_table(raw, enf) -> pd.DataFrame:
    rows = []
    recs = adequacy_records()
    for dom in DOMAINS:
        rs = [r for r in recs.values() if r["domain"] == dom]
        if not rs:
            continue
        for r in rs:
            m, ci = r["validation_primary"]["metrics"], r["validation_primary"]["bootstrap"]["ci"]
            st = r["decision"]["status"]
            rr = cold(raw[(raw["domain"] == dom) & (raw["objective"] == r["objective"]) & (raw["method"] == "AVOI")])
            ee = cold(enf[(enf["domain"] == dom) & (enf["objective"] == r["objective"]) & (enf["method"] == "AVOI")])
            a, b = SA.rates(rr), SA.rates(ee)
            rows.append({"domain": DOM_LABEL[dom], "model": r["objective"],
                         "discrimination": f"AUROC {m['AUROC']:.3f} [{ci['AUROC'][0]:.3f}, {ci['AUROC'][1]:.3f}]; PR skill {m['PR_skill']:.3f} [{ci['PR_skill'][0]:.3f}, {ci['PR_skill'][1]:.3f}]",
                         "calibration": f"BSS {m['BSS']:.3f}; ECE {m['ECE']:.3f}; slope {m['calibration_slope']:.2f}",
                         "sample_support": f"{m['n_violated']} violated / {r['validation_primary']['bootstrap']['n_groups']} groups",
                         "adequacy_status": st, "autonomous_AVOI_permitted": st == AQ.VALIDATED,
                         "ungated_UAR": a["UAR"], "gated_UAR": b["UAR"], "ungated_coverage": a["coverage"], "gated_coverage": b["coverage"]})
    return pd.DataFrame(rows)


def matched_tables(raw) -> tuple[pd.DataFrame, pd.DataFrame]:
    tun = aux("tuning")
    cov_rows, safe_rows = [], []
    p = raw[(raw["experiment"] == "primary") & (raw["condition"] == PRIMARY_COND) & (raw["start"] == "cold")]
    for dom in DOMAINS:
        for mth in [m for m in METHODS if m != "B2-Random"] + ["B2-Random[s0]"]:
            for tgt in sorted(p["shift"].unique()):
                if not str(tgt).startswith("target:"):
                    continue
                sub = p[(p["domain"] == dom) & (p["method"] == mth) & (p["shift"] == tgt)]
                t = tun[(tun["domain"] == dom) & (tun["method"] == mth) & (tun.get("target") == tgt) & (tun["experiment"] == "primary")] if "target" in tun else pd.DataFrame()
                n_all = t["objective"].nunique() if not t.empty else 0
                n_ok = int(t["target_achieved_validation"].fillna(False).astype(bool).sum()) if not t.empty else 0
                base = {"domain": DOM_LABEL[dom], "method": DISPLAY.get(mth.replace("[s0]", ""), mth), "target": tgt.replace("target:", ""),
                        "models_achieving_target_on_validation": f"{n_ok}/{n_all}"}
                if sub.empty:
                    row = {**base, "status": "not achieved (validation)"}
                else:
                    s = boot_summary(sub)
                    row = {**base, "status": "achieved" if n_ok == n_all else "partially achieved",
                           "confirmation_UAR": ci_str(s["point"]["UAR"], *s["ci"]["UAR"]), "confirmation_coverage": ci_str(s["point"]["coverage"], *s["ci"]["coverage"]),
                           "confirmation_cost": ci_str(s["point"]["normalized_cost"], *s["ci"]["normalized_cost"], 4),
                           "confirmation_acquisitions": ci_str(s["point"]["mean_acquisitions"], *s["ci"]["mean_acquisitions"]),
                           "episodes": s["n"]}
                (cov_rows if "coverage=" in tgt and "uar" not in tgt else safe_rows).append(row)
    return pd.DataFrame(cov_rows), pd.DataFrame(safe_rows)


def budget_table() -> pd.DataFrame:
    b = aux("budget")
    rows = []
    for (dom, mth, k), g in b.groupby(["domain", b["method"].str.replace(r"\[s\d+\]", "", regex=True), "budget"]):
        if mth not in METHODS:
            continue
        r = SA.rates(g)
        rows.append({"domain": dom, "method": DISPLAY.get(mth, mth), "max_acquisitions_k": int(k), "expected_loss": float(g["loss"].mean()),
                     "UAR": r["UAR"], "FAA": r["FAA"], "coverage": r["coverage"], "mean_acquisitions": float(g["n_acq"].mean()),
                     "max_observed_acquisitions": int(g["n_acq"].max()), "share_stopping_before_k": float((g["n_acq"] < k).mean()),
                     "episodes": len(g)})
    return pd.DataFrame(rows)


def missingness_table(raw, enf) -> pd.DataFrame:
    rows = []
    for mode_name, df in (("raw", raw), ("enforced", enf)):
        d = df[(df["experiment"] == "primary") & (df["condition"] == PRIMARY_COND) & (df["shift"] == "none")]
        for (dom, mth, mm, lvl), g in d.groupby(["domain", "method", "missing_mode", "missing_level"]):
            if mth not in METHODS or mth == "B2-Random":
                continue
            r = SA.rates(g)
            modes = ["mcar", "block", "adversarial"] if mm == "none" else [mm]
            for mo in modes:
                rows.append({"adequacy_mode": mode_name, "domain": dom, "method": DISPLAY.get(mth, mth), "missing_mode": mo,
                             "initially_unacquired_pct": int(round(100 * lvl)), "expected_loss": float(g["loss"].mean()), "UAR": r["UAR"],
                             "FAA": r["FAA"], "coverage": r["coverage"], "human_review_rate": r["human_review_rate"],
                             "mean_acquisitions": float(g["n_acq"].mean()), "cost": float(g["cost"].mean()), "privacy": float(g["privacy"].mean()),
                             "mean_initial_entropy": float(g["initial_entropy"].mean()), "episodes": len(g)})
    return pd.DataFrame(rows)


def privacy_table(raw) -> pd.DataFrame:
    d = raw[(raw["experiment"] == "privacy") & (raw["start"] == "cold") & (raw["shift"] == "none")]
    rows = []
    for (dom, cond), g in d.groupby(["domain", "condition"]):
        mu = float(cond.split("mu=")[1].split("|")[0])
        r = SA.rates(g)
        rows.append({"domain": dom, "mu": mu, "privacy_exposure": float(g["privacy"].mean()), "expected_loss": float(g["loss"].mean()),
                     "UAR": r["UAR"], "coverage": r["coverage"], "mean_acquisitions": float(g["n_acq"].mean()), "cost": float(g["cost"].mean()),
                     "episodes": len(g)})
    return pd.DataFrame(rows).sort_values(["domain", "mu"])


def ablation_table(raw) -> pd.DataFrame:
    rows = []
    for dom in DOMAINS:
        d = cold(raw[raw["domain"] == dom], "ablation")
        for mth in ["AVOI", "A1-NoAsymmetricLoss", "A2-NoLearnedReliability", "A3-NoCost", "A4-NoPrivacy", "A5-NoDelay", "A6-NoEscalation",
                    "A7-EntropyInsteadOfRisk", "A8-NaiveBayesModel"]:
            x = per_method(d, mth)
            if not x.empty:
                rows.append(method_row(x, mth, {"domain": DOM_LABEL[dom]}))
        # gate ablation: AVOI with vs without the adequacy gate
    return strip(rows)


def asymmetric_ablation(raw) -> pd.DataFrame:
    rows = []
    for dom in DOMAINS:
        d = cold(raw[raw["domain"] == dom], "ablation")
        a, s = per_method(d, "AVOI"), per_method(d, "A1-NoAsymmetricLoss")
        if a.empty or s.empty:
            continue
        for metric in ("UAR", "FAA", "expected_loss", "mean_acquisitions", "coverage", "human_review_rate"):
            est, lo, hi = boot_diff(a, s, metric)
            ra, rs = boot_summary(a)["point"][metric], boot_summary(s)["point"][metric]
            rows.append({"domain": DOM_LABEL[dom], "metric": metric, "AVOI_asymmetric_10_2_1": ra, "symmetric_2_2_1": rs,
                         "difference_asymmetric_minus_symmetric": ci_str(est, lo, hi, 4)})
        va = a[a["y"] == 0].merge(s[s["y"] == 0], on=["objective", "episode_id", "group"], suffixes=("_a", "_s"))
        mc = MT.mcnemar_exact((va["decision_a"] == "Assured").to_numpy(), (va["decision_s"] == "Assured").to_numpy())
        rows.append({"domain": DOM_LABEL[dom], "metric": "McNemar exact (unsafe assurance, Y=0)", "AVOI_asymmetric_10_2_1": mc["discordant_method_only"],
                     "symmetric_2_2_1": mc["discordant_comparator_only"], "difference_asymmetric_minus_symmetric": f"p={mc['p']:.3g}"})
    return pd.DataFrame(rows)


def escalation_table(raw, enf) -> pd.DataFrame:
    rows = []
    for dom in DOMAINS:
        for o in sorted(raw[raw["domain"] == dom]["objective"].unique()):
            r = cold(raw[(raw["domain"] == dom) & (raw["objective"] == o) & (raw["method"] == "AVOI")])
            e = cold(enf[(enf["domain"] == dom) & (enf["objective"] == o) & (enf["method"] == "AVOI")])
            ev = SA.escalation_breakdown(r, LOSS)
            gt = SA.gate_breakdown(r, e)
            rows.append({"domain": dom, "objective": o, "adequacy_status": status_of(dom, o), "type": "evidence-uncertainty escalation (raw AVOI)",
                         **{k: v for k, v in ev.items()}})
            rows.append({"domain": dom, "objective": o, "adequacy_status": status_of(dom, o), "type": "model-adequacy escalation (gate)",
                         "escalations": gt["gated_episodes"], "Y0": gt["Y0"], "Y1": gt["Y1"], "false_assurances_prevented": gt["false_assurances_prevented"],
                         "false_non_assurances_prevented": gt["false_non_assurances_prevented"], "correct_autonomous_withheld": gt["correct_autonomous_withheld"],
                         "decisions_changed": gt["decisions_changed"], "coverage_lost": gt["coverage_raw"] - gt["coverage_enforced"]})
    return pd.DataFrame(rows)


def zero_acq_table(raw) -> pd.DataFrame:
    rows = []
    for dom in DOMAINS:
        d = cold(raw[raw["domain"] == dom])
        for mth in METHODS:
            if mth == "B2-Random":
                continue
            x = d[d["method"] == mth]
            if x.empty:
                continue
            n = x["n_acq"]
            req = x[x["acquisition_required"] == True]
            rr = SA.rates(req) if len(req) else {}
            rows.append({"domain": dom, "method": DISPLAY.get(mth, mth), "P(N_acq=0)": float((n == 0).mean()), "P(N_acq>0)": float((n > 0).mean()),
                         "E[N_acq]": float(n.mean()), "E[N_acq | N_acq>0]": float(n[n > 0].mean()) if (n > 0).any() else np.nan,
                         "acquisition_required_share": float(len(req) / len(x)), "acq_required_UAR": rr.get("UAR", np.nan),
                         "acq_required_coverage": rr.get("coverage", np.nan), "acq_required_expected_loss": float(req["loss"].mean()) if len(req) else np.nan,
                         "acq_required_mean_acquisitions": float(req["n_acq"].mean()) if len(req) else np.nan})
    return pd.DataFrame(rows)


def statistics_table(raw) -> pd.DataFrame:
    """Paired tests on confirmation episodes of VALIDATED models only (raw acquisition policies)."""
    rows = []
    for dom in DOMAINS:
        d = cold(raw[raw["domain"] == dom])
        ok = [o for o in d["objective"].unique() if status_of(dom, o) == AQ.VALIDATED]
        d = d[d["objective"].isin(ok)]
        if d.empty:
            continue
        a = per_method(d, "AVOI")
        block = []
        for comp in [m for m in METHODS if m != "AVOI"]:
            b = per_method(d, comp)
            keys = ["objective", "episode_id", "y", "group"]
            m = a.merge(b, on=keys, suffixes=("_a", "_b"))
            for metric, col in (("mean_acquisitions", "n_acq"), ("normalized_cost", "cost"), ("expected_loss", "loss"), ("privacy_exposure", "privacy")):
                w = MT.wilcoxon_paired(m[f"{col}_a"].to_numpy(float), m[f"{col}_b"].to_numpy(float))
                est, lo, hi = boot_diff(a, b, metric)
                block.append({"domain": DOM_LABEL[dom], "models": ", ".join(ok), "comparison": f"AVOI vs {DISPLAY[comp]}", "metric": metric,
                              "test": "Wilcoxon signed-rank", "statistic": w["statistic"], "p": w["p"], "effect": "rank-biserial",
                              "effect_size": w["effect_rank_biserial"], "difference": est, "ci_low": lo, "ci_high": hi, "n_pairs": len(m)})
            v = m[m["y"] == 0]
            if comp == "B2-Random":
                t = MT.signflip_permutation(((v["decision_a"] == "Assured").astype(float)).to_numpy(), v["assured_f"].to_numpy())
                test, stat, eff, effn = "sign-flip permutation", t["statistic"], t["effect_mean_difference"], "mean difference"
            else:
                t = MT.mcnemar_exact((v["decision_a"] == "Assured").to_numpy(), (v["decision_b"] == "Assured").to_numpy())
                test, stat, eff, effn = "exact McNemar", t["statistic"], t["effect_discordant_odds_ratio"], "discordant odds ratio"
            est, lo, hi = boot_diff(a, b, "UAR")
            block.append({"domain": DOM_LABEL[dom], "models": ", ".join(ok), "comparison": f"AVOI vs {DISPLAY[comp]}", "metric": "UAR", "test": test,
                          "statistic": stat, "p": t["p"], "effect": effn, "effect_size": eff, "difference": est, "ci_low": lo, "ci_high": hi, "n_pairs": len(v)})
        bd = pd.DataFrame(block)
        for metric, g in bd.groupby("metric"):
            bd.loc[g.index, "p_holm"] = MT.holm(g["p"].tolist())
        rows.append(bd)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def fa_table(raw) -> pd.DataFrame:
    d = raw[(raw["experiment"] == "fa_sensitivity") & (raw["start"] == "cold") & (raw["shift"] == "none")]
    rows = []
    for (dom, cond, mth), g in d.groupby(["domain", "condition", "method"]):
        r = SA.rates(g)
        rows.append({"domain": dom, "false_assurance_penalty": float(cond.split("fa=")[1].split("|")[0]), "method": DISPLAY.get(mth, mth),
                     "UAR": r["UAR"], "coverage": r["coverage"], "mean_cost": float(g["cost"].mean()),
                     "expected_loss_under_that_penalty": float(g["loss"].mean()), "episodes": len(g)})
    return pd.DataFrame(rows).sort_values(["domain", "method", "false_assurance_penalty"])


def adequacy_sensitivity(raw) -> pd.DataFrame:
    pol = AQ.load_policy()
    sens = pol["sensitivity"]
    recs = adequacy_records()
    rows = []
    grid = [("primary", {})]
    grid += [(f"ECE<={v}", {("calibration", "ece_le"): v}) for v in sens["ece_le"]]
    grid += [(f"slope in [{a},{b}]", {("calibration", "slope_min"): a, ("calibration", "slope_max"): b}) for a, b in sens["slope_interval"]]
    grid += [(f"AUROC CI lower>{v}", {("discrimination", "auroc_ci_lower_gt"): v}) for v in sens["auroc_ci_lower_gt"]]
    grid += [(f"min violated>={v}", {("support", "min_violated_cases"): v}) for v in sens["min_violated_cases"]]
    avoi = cold(raw[raw["method"] == "AVOI"])
    for name, ov in grid:
        stat = {}
        for key, r in recs.items():
            d = AQ.decide(r["decision"]["model_id"], r["validation_primary"]["metrics"], r["validation_primary"]["bootstrap"], pol,
                          r["decision"]["calibrator"], overrides=ov, groups_with_violation=r["groups_with_violation"])
            stat[(r["domain"], r["objective"])] = d.status
        gated = avoi.copy()
        blocked = gated.apply(lambda x: stat[(x["domain"], x["objective"])] != AQ.VALIDATED, axis=1)
        gated.loc[blocked, "decision"] = HUMAN_REVIEW
        gated.loc[blocked, "loss"] = LOSS.human_review
        for dom in DOMAINS + ["all"]:
            g = gated if dom == "all" else gated[gated["domain"] == dom]
            if g.empty:
                continue
            sts = [v for (dd, _), v in stat.items() if dom in ("all", dd)]
            r = SA.rates(g)
            rows.append({"policy_variant": name, "domain": dom, "models_validated": sum(s == AQ.VALIDATED for s in sts),
                         "models_restricted": sum(s == AQ.RESTRICTED for s in sts), "models_unsupported": sum(s == AQ.UNSUPPORTED for s in sts),
                         "autonomous_coverage": r["coverage"], "UAR": r["UAR"], "expected_loss": float(g["loss"].mean()),
                         "human_review_rate": r["human_review_rate"], "is_primary_policy": name == "primary"})
    return pd.DataFrame(rows)


def risk_coverage_table() -> pd.DataFrame:
    rows = []
    for mode in ("raw", "enforced"):
        c = aux("curves", mode)
        c = c[(c["experiment"] == "primary")]
        c["method_family"] = c["method"].str.replace(r"\[s\d+\]", "", regex=True)
        for (dom, mth), g in c.groupby(["domain", "method_family"]):
            p = g.groupby("tau", dropna=False)[["n", "n_viol", "n_hr", "n_unsafe", "loss_sum", "cost_sum"]].sum().reset_index()
            p["coverage"] = 1 - p["n_hr"] / p["n"]
            p["UAR"] = p["n_unsafe"] / p["n_viol"]
            q = p.dropna(subset=["UAR"]).groupby("coverage", as_index=False)["UAR"].min().sort_values("coverage")
            span = q["coverage"].max() - q["coverage"].min() if len(q) else 0
            aurc = float(np.trapezoid(q["UAR"], q["coverage"]) / span) if span > 0 else np.nan
            rows.append({"adequacy_mode": mode, "domain": dom, "method": DISPLAY.get(mth, mth), "coverage_range": f"{q['coverage'].min():.3f}-{q['coverage'].max():.3f}" if len(q) else "",
                         "AURC_UAR_normalized": aurc, "UAR_denominator_constant": bool(p["n_viol"].nunique() == 1), "thresholds": len(p)})
    return pd.DataFrame(rows)


def pareto_distance(raw) -> pd.DataFrame:
    c = aux("curves", "raw")
    c = c[c["experiment"] == "primary"]
    c["method_family"] = c["method"].str.replace(r"\[s\d+\]", "", regex=True)
    rows = []
    for dom, gd in c.groupby("domain"):
        pts = []
        for (mth, tau), g in gd.groupby(["method_family", "tau"], dropna=False):
            s = g[["n", "n_viol", "n_unsafe", "loss_sum", "cost_sum"]].sum()
            pts.append({"method": mth, "tau": tau, "cost": s["cost_sum"] / s["n"], "loss": s["loss_sum"] / s["n"]})
        P = pd.DataFrame(pts)
        X = P[["cost", "loss"]].to_numpy()
        rng_ = X.max(0) - X.min(0)
        rng_[rng_ == 0] = 1
        Z = (X - X.min(0)) / rng_
        front = np.array([not np.any(np.all(Z <= z, 1) & np.any(Z < z, 1)) for z in Z])
        F = Z[front]
        P["dist"] = [float(np.min(np.linalg.norm(np.maximum(z - F, 0), axis=1))) for z in Z]
        for mth, g in P.groupby("method"):
            rows.append({"domain": dom, "method": DISPLAY.get(mth, mth), "configurations": len(g),
                         "min_normalized_distance_to_frontier": float(g["dist"].min()), "median_distance": float(g["dist"].median())})
    return pd.DataFrame(rows)


def stage1_recovered() -> pd.DataFrame:
    t = pd.read_csv(ROOT / "results" / "stage1_ungated" / "tables" / "table3_main_comparison.csv")
    t = t[t["method"].isin(["AVOI-GRC", "B0-AllEvidence", "B4-InformationGain", "B5-GenericVOI", "B6-ConfidenceThreshold"])].copy()
    t["method"] = t["method"].replace({"AVOI-GRC": "AVOI"})
    t.insert(0, "study_stage", "Stage 1 (original, ungated)")
    return t[["study_stage", "dataset", "method", "UAR", "expected_loss", "mean_acquisitions", "coverage"]]


def llm_table() -> pd.DataFrame:
    p = S2 / "raw" / "llm_planner" / "episodes_llm_planner.csv.gz"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    df["group"] = df["group"].astype(str)
    rows = []
    for (mode, m), g in df.groupby(["adequacy_mode", "method"]):
        s = boot_summary(g, 2000)
        rows.append({"adequacy_mode": mode, "method": m, "episodes": s["n"], "UAR": ci_str(s["point"]["UAR"], *s["ci"]["UAR"]),
                     "expected_loss": ci_str(s["point"]["expected_loss"], *s["ci"]["expected_loss"]),
                     "mean_acquisitions": ci_str(s["point"]["mean_acquisitions"], *s["ci"]["mean_acquisitions"]),
                     "coverage": ci_str(s["point"]["coverage"], *s["ci"]["coverage"])})
    info = json.loads((S2 / "raw" / "llm_planner" / "run_info.json").read_text())
    out = pd.DataFrame(rows)
    out["note"] = f"secondary; {info['model']}; {info['subset']}; invalid responses {info['invalid_responses']}"
    return out


# ====================================================================================== hypotheses S1-S4
def hypotheses(raw, enf, stats: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dec = decisions()
    nonval = [k for k, v in dec.items() if v["status"] != AQ.VALIDATED]
    val = [k for k, v in dec.items() if v["status"] == AQ.VALIDATED]
    avoi = cold(raw[raw["method"] == "AVOI"])
    key = avoi["domain"] + "|" + avoi["objective"]
    # S1
    if not nonval or not val:
        rows.append({"hypothesis": "S1", "verdict": "not testable", "details": f"validated={len(val)}, non-validated={len(nonval)}"})
    else:
        a, b = avoi[key.isin(nonval)], avoi[key.isin(val)]
        det = []
        sig = False
        for metric in ("UAR", "expected_loss"):
            sa, sb = boot_summary(a), boot_summary(b)
            # independent groups: bootstrap difference of two pooled estimates
            rng = np.random.default_rng(7)
            ia = _indicators(a).groupby("group").sum(numeric_only=True)
            ib = _indicators(b).groupby("group").sum(numeric_only=True)
            Wa = rng.multinomial(len(ia), np.full(len(ia), 1 / len(ia)), size=N_BOOT)
            Wb = rng.multinomial(len(ib), np.full(len(ib), 1 / len(ib)), size=N_BOOT)
            da = _metrics_from_sums({c: Wa @ ia[c].to_numpy() for c in ia.columns})[metric]
            db = _metrics_from_sums({c: Wb @ ib[c].to_numpy() for c in ib.columns})[metric]
            diff = da - db
            lo, hi = float(np.nanquantile(diff, 0.025)), float(np.nanquantile(diff, 0.975))
            det.append(f"{metric}: non-validated {sa['point'][metric]:.4f} vs validated {sb['point'][metric]:.4f}, difference CI [{lo:.4f}, {hi:.4f}]")
            sig = sig or lo > 0
        rows.append({"hypothesis": "S1", "verdict": "supported" if sig else "partially supported",
                     "details": f"non-validated models: {nonval}; " + " | ".join(det)})
    # S2
    e = cold(enf[enf["method"] == "AVOI"])
    ke = e["domain"] + "|" + e["objective"]
    blocked = e[ke.isin(nonval)]
    passed = e[ke.isin(val)]
    r_passed = avoi[key.isin(val)]
    cond1 = (blocked["decision"] != HUMAN_REVIEW).sum() == 0
    cond2 = blocked["reason"].isin(["MODEL_ADEQUACY_RESTRICTED", "MODEL_ADEQUACY_UNSUPPORTED"]).all() if len(blocked) else True
    cond3 = (passed.sort_values(["objective", "episode_id"])["decision"].to_numpy() == r_passed.sort_values(["objective", "episode_id"])["decision"].to_numpy()).all()
    if not nonval:
        verdict = "not testable (all models VALIDATED)"
    else:
        verdict = "supported" if (cond1 and cond2 and cond3) else "not supported"
    rows.append({"hypothesis": "S2", "verdict": verdict, "details": f"autonomous decisions for non-validated models: {int((blocked['decision'] != HUMAN_REVIEW).sum())}; "
                 f"correct gate reasons: {bool(cond2)}; validated models unaffected: {bool(cond3)}"})
    # S3
    for dom in DOMAINS:
        s = stats[(stats["domain"] == DOM_LABEL[dom]) & (stats["metric"] == "mean_acquisitions")] if not stats.empty else pd.DataFrame()
        s = s[s["comparison"].isin(["AVOI vs Checklist", "AVOI vs All Evidence"])] if not s.empty else s
        if s.empty:
            rows.append({"hypothesis": "S3", "domain": DOM_LABEL[dom], "verdict": "not testable (no VALIDATED model)", "details": ""})
            continue
        adj = MT.holm(s["p"].tolist())
        ok = all(pa < 0.05 and hi < 0 for pa, hi in zip(adj, s["ci_high"]))
        det = "; ".join(f"{r.comparison}: diff {r.difference:+.3f} [{r.ci_low:+.3f}, {r.ci_high:+.3f}], Holm p={pa:.3g}" for r, pa in zip(s.itertuples(), adj))
        lossinfo = stats[(stats["domain"] == DOM_LABEL[dom]) & (stats["metric"].isin(["expected_loss", "UAR"])) & stats["comparison"].isin(["AVOI vs Checklist", "AVOI vs All Evidence"])]
        det += " | context (not part of the rule): " + "; ".join(f"{r.comparison} {r.metric} diff {r.difference:+.4f} [{r.ci_low:+.4f}, {r.ci_high:+.4f}]" for r in lossinfo.itertuples())
        rows.append({"hypothesis": "S3", "domain": DOM_LABEL[dom], "verdict": "supported" if ok else "not supported", "details": det})
    # S4
    if not nonval:
        rows.append({"hypothesis": "S4", "verdict": "not testable (all models VALIDATED)", "details": ""})
    else:
        det, ok = [], True
        for k in nonval:
            dom, o = k.split("|")
            dU, uLo, uHi = boot_diff(e[ke == k], avoi[key == k], "UAR")
            dC, cLo, cHi = boot_diff(e[ke == k], avoi[key == k], "coverage")
            det.append(f"{k}: dUAR {dU:+.4f} [{uLo:+.4f}, {uHi:+.4f}], dCoverage {dC:+.4f} [{cLo:+.4f}, {cHi:+.4f}]")
            if abs(dU) > 0 and not dC < 0:
                ok = False
        rows.append({"hypothesis": "S4", "verdict": "supported" if ok else "not supported", "details": " | ".join(det)})
    return pd.DataFrame(rows)


def build_all() -> dict:
    TABLES.mkdir(parents=True, exist_ok=True)
    raw, enf = episodes("raw"), episodes("enforced")
    out = {}
    ma, pre = table_model_adequacy()
    out["model_adequacy"] = write(ma, "table_model_adequacy", "Stage 2. Evidence-model adequacy on the adequacy-validation partition (95% group-bootstrap CI, 5,000 resamples)")
    write(pre, "table_calibration_pre_post", "Stage 2 (supplementary). Calibration before/after the development-selected calibrator")
    mt = main_tables(raw, enf)
    out["main_raw"] = write(strip(mt["raw_all_models"]), "main_comparison_raw", "Stage 2 confirmation: RAW acquisition-policy comparison (no adequacy gate), all evidence models")
    out["main_enforced"] = write(strip(mt["enforced_all_models"]), "main_comparison_enforced", "Stage 2 confirmation: SAFETY-AWARE comparison (identical adequacy eligibility applied to every model-based method)")
    out["main_validated"] = write(strip(mt["raw_validated_models"]), "main_comparison_validated_models", "Stage 2 confirmation: PRIMARY evaluation restricted to VALIDATED evidence models")
    out["gate_effect"] = write(gate_effect(raw, enf), "adequacy_gate_effect", "Stage 2. Adequacy-gate effect on AVOI (UAR and coverage reported jointly)")
    out["boundary"] = write(boundary_table(raw, enf), "table_boundary", "Stage 2. Model-adequacy boundary: a good acquisition strategy cannot compensate for an inadequate evidence model")
    cov, safe = matched_tables(raw)
    out["matched_coverage"] = write(cov, "matched_coverage", "Stage 2. Matched autonomous coverage (thresholds selected on validation; confirmation results)")
    out["matched_safety"] = write(safe, "matched_safety_nondegenerate", "Stage 2. Non-degenerate matched safety: minimum cost s.t. UAR <= eta AND coverage >= gamma (validation-selected)")
    out["budget"] = write(budget_table(), "budget", "Stage 2. Hard evidence budget (AT MOST k acquisitions)")
    out["missingness"] = write(missingness_table(raw, enf), "missingness", "Stage 2. Missing-evidence robustness (loss, UAR, FAA, coverage, HumanReview, acquisitions, cost, privacy)")
    out["privacy"] = write(privacy_table(raw), "privacy", "Stage 2. Privacy-weight sensitivity (actual mu values; privacy exposure is an experimental proxy)")
    out["ablation"] = write(ablation_table(raw), "ablation", "Stage 2. Ablations (confirmation, raw acquisition policy); 'AVOI - adequacy gate' = main_comparison_raw vs enforced")
    out["asymmetric"] = write(asymmetric_ablation(raw), "asymmetric_loss_ablation", "Stage 2. Asymmetric assurance loss (10:2:1) vs otherwise identical symmetric-loss AVOI (2:2:1)")
    out["escalation"] = write(escalation_table(raw, enf), "escalation", "Stage 2. Evidence-uncertainty vs model-adequacy escalation (AVOI)")
    out["zero_acquisition"] = write(zero_acq_table(raw), "zero_acquisition", "Stage 2. Zero-acquisition episodes and acquisition-required subset")
    stats = statistics_table(raw)
    out["statistics"] = write(stats, "statistics", "Stage 2. Paired tests on confirmation episodes of VALIDATED models (Holm within metric)")
    out["fa"] = write(fa_table(raw), "fa_sensitivity", "Stage 2. False-assurance penalty sensitivity (expected loss is on the scale of each penalty)")
    out["adequacy_sensitivity"] = write(adequacy_sensitivity(raw), "adequacy_sensitivity", "Stage 2. Adequacy-policy sensitivity (primary policy unchanged)")
    out["risk_coverage"] = write(risk_coverage_table(), "risk_coverage_aurc", "Stage 2. Risk-coverage summary (raw and adequacy-enforced)")
    out["pareto"] = write(pareto_distance(raw), "pareto_distance", "Stage 2. Normalized distance to the global cost-loss Pareto frontier (per method)")
    out["stage1"] = write(stage1_recovered(), "stage1_recovered_results", "Stage 1 (original, ungated) results recovered from the archive")
    llm = llm_table()
    if not llm.empty:
        out["llm"] = write(llm, "llm_planner", "Stage 2 (secondary). LLM-only planner gemma4:e4b vs AVOI")
    hyp = hypotheses(raw, enf, stats)
    out["hypotheses"] = write(hyp, "stage2_hypotheses", "Stage-2 hypotheses S1-S4")
    return out
