"""Statistical analysis and CSV result tables."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from avoi.evaluation import analysis_data as AD
from avoi.evaluation import metrics as MT

ROOT = Path(__file__).resolve().parents[3]
TABLES = ROOT / "results" / "tables"
SEED = 20260914


# ---------------------------------------------------------------------------------------------- writers
def fmt(v, digits=3):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return f"{v:.{digits}f}"
    return str(v)


def write_table(df: pd.DataFrame, name: str, caption: str = "") -> dict:
    TABLES.mkdir(parents=True, exist_ok=True)
    path = TABLES / f"{name}.csv"
    df.to_csv(path, index=False)
    return {"name": name, "csv": path.relative_to(ROOT).as_posix()}


def ci_str(est, lo, hi, d=3):
    return f"{fmt(est, d)} [{fmt(lo, d)}, {fmt(hi, d)}]"


# ---------------------------------------------------------------------------------------------- method summaries
def summarize_method(df: pd.DataFrame, method: str, n_boot=MT.N_BOOT) -> dict:
    x = AD.per_method(df, method)
    if x.empty:
        return {}
    if method == "B2-Random":
        seeds = df[df["method_family"] == "B2-Random"]
        per_seed = pd.DataFrame([MT.decision_metrics(g) for _, g in seeds.groupby("method")])
        point = per_seed.mean(numeric_only=True).to_dict()
        point["seed_sd_UAR"] = float(per_seed["UAR"].std())
        point["seed_sd_expected_loss"] = float(per_seed["expected_loss"].std())
        a = {"y": x["y"].to_numpy(float), "viol": (x["y"] == 0).to_numpy(float), "belief": x["belief"].to_numpy(float),
             "loss": x["loss"].to_numpy(float), "assured": x["assured_f"].to_numpy(float), "hr": x["hr_f"].to_numpy(float),
             "auto": 1 - x["hr_f"].to_numpy(float), "n_acq": x["n_acq"].to_numpy(float), "cost": x["cost"].to_numpy(float),
             "privacy": x["privacy"].to_numpy(float), "delay": x["delay"].to_numpy(float), "unsafe": x["unsafe_frac"].to_numpy(float),
             "tp": ((x["belief"] < 0.5) & (x["y"] == 0)).to_numpy(float), "tn": ((x["belief"] >= 0.5) & (x["y"] == 1)).to_numpy(float)}
        I = MT.stratified_indices(x["y"].to_numpy(), n_boot, SEED)
        ci = {}
        for m in ("UAR", "FAR_A", "expected_loss", "coverage", "escalation_rate", "mean_acquisitions", "normalized_cost",
                  "privacy_exposure", "Brier", "balanced_accuracy"):
            v = MT.FAST[m](a, I)
            v = v[~np.isnan(v)]
            ci[m] = (float(np.quantile(v, .025)), float(np.quantile(v, .975))) if len(v) else (np.nan, np.nan)
    else:
        point = MT.decision_metrics(x)
        ci = MT.bootstrap_ci(x, ["UAR", "FAR_A", "expected_loss", "coverage", "escalation_rate", "mean_acquisitions",
                                 "normalized_cost", "privacy_exposure", "Brier", "balanced_accuracy"], n_boot, SEED)
    point["ci"] = ci
    return point


MAIN_COLS = ["UAR", "FAR_A", "expected_loss", "balanced_accuracy", "macro_f1", "MCC", "coverage", "escalation_rate",
             "mean_acquisitions", "median_acquisitions", "normalized_cost", "privacy_exposure", "Brier", "ECE"]


def main_table(domains: list[str], experiment="primary", methods=None, name="table3_main_comparison",
               caption="Table 3. Main method comparison on held-out episodes (primary condition; 95% bootstrap CIs)") -> tuple[pd.DataFrame, dict]:
    methods = methods or AD.MAIN_METHODS
    rows, store = [], {}
    for dom in domains:
        df = AD.tuned(experiment, dom)
        if df.empty:
            continue
        for mth in methods:
            s = summarize_method(df, mth)
            if not s:
                continue
            store[(dom, mth)] = s
            r = {"dataset": dom, "method": mth, "n_episodes": s.get("n")}
            for c in MAIN_COLS:
                if c in s.get("ci", {}):
                    r[c] = ci_str(s[c], *s["ci"][c])
                else:
                    r[c] = fmt(s.get(c))
            rows.append(r)
    # macro average across datasets (dataset-level point estimates; no pooling of raw episodes)
    for mth in methods:
        vals = [store[(d, mth)] for d in domains if (d, mth) in store]
        if len(vals) >= 2:
            r = {"dataset": f"macro({len(vals)} datasets)", "method": mth, "n_episodes": sum(v["n"] for v in vals)}
            for c in MAIN_COLS:
                r[c] = fmt(float(np.nanmean([v.get(c, np.nan) for v in vals])))
            rows.append(r)
    t = pd.DataFrame(rows)
    return t, store


# ---------------------------------------------------------------------------------------------- paired statistics
def paired_stats(domain: str, experiment="primary", comparators=None, proposed="AVOI-GRC") -> pd.DataFrame:
    df = AD.tuned(experiment, domain)
    comparators = comparators or [m for m in AD.MAIN_METHODS if m != proposed]
    rows = []
    for comp in comparators:
        p = AD.paired_frame(df, proposed, comp)
        if p.empty:
            continue
        strata = p["y"].to_numpy()
        for metric, col in (("expected_loss", "loss"), ("acquisitions", "n_acq"), ("normalized_cost", "cost"),
                            ("privacy_exposure", "privacy")):
            xa, xb = p[f"{col}_a"].to_numpy(float), p[f"{col}_b"].to_numpy(float)
            test = MT.wilcoxon_paired(xa, xb)
            est, lo, hi = MT.paired_bootstrap_diff(xa, xb, strata, seed=SEED)
            rows.append({"dataset": domain, "comparison": f"{proposed} vs {comp}", "metric": metric, **test,
                         "mean_difference": est, "ci_low": lo, "ci_high": hi, "n_pairs": len(p)})
        viol = p["y"] == 0
        ua = ((p["decision_a"] == "Assured") & viol).to_numpy(float)
        if comp == "B2-Random":
            ub = p["unsafe_frac_b"].to_numpy(float) if "unsafe_frac_b" in p else p["unsafe_frac"].to_numpy(float)
            test = MT.signflip_permutation(ua[viol.to_numpy()], ub[viol.to_numpy()], seed=SEED)
        else:
            ub = ((p["decision_b"] == "Assured") & viol).to_numpy(float)
            test = MT.mcnemar_exact(ua[viol.to_numpy()].astype(bool), ub[viol.to_numpy()].astype(bool))
        est, lo, hi = MT.paired_bootstrap_diff(ua, ub, strata, seed=SEED, denom=viol.to_numpy(float))
        rows.append({"dataset": domain, "comparison": f"{proposed} vs {comp}", "metric": "UAR", **test,
                     "mean_difference": est, "ci_low": lo, "ci_high": hi, "n_pairs": int(viol.sum())})
    out = pd.DataFrame(rows)
    if not out.empty:
        out["p_holm"] = np.nan
        for (d, m), g in out.groupby(["dataset", "metric"]):
            out.loc[g.index, "p_holm"] = MT.holm(g["p"].tolist())
    return out


def friedman_table(domain: str, experiment="primary", methods=None) -> dict:
    df = AD.tuned(experiment, domain)
    methods = methods or [m for m in AD.MAIN_METHODS]
    blocks = {}
    for m in methods:
        x = AD.per_method(df, m)
        if x.empty:
            continue
        blocks[m] = x.groupby(["objective", "fold"])["loss"].mean()
    return MT.friedman(pd.DataFrame(blocks))


# ---------------------------------------------------------------------------------------------- matched tables
def target_table(domains, kind: str) -> pd.DataFrame:
    rows = []
    targets = {"coverage": [0.6, 0.7, 0.8, 0.9], "uar": [0.01, 0.02, 0.05]}[kind]
    for dom in domains:
        df = AD.episodes("primary", dom)
        tun = AD.table("primary", dom, "tuning")
        if df.empty:
            continue
        for mth in [m for m in AD.MAIN_METHODS if m != "B2-Random"] + ["B2-Random[s0]"]:
            for t in targets:
                tag = f"target:coverage={t}" if kind == "coverage" else f"target:uar<={t}"
                sub = df[(df["method"] == mth) & (df["shift"] == tag) & (df["condition"] == AD.PRIMARY_COND)]
                folds_total = tun[(tun["method"] == mth) & (tun.get("target") == tag)] if "target" in tun else pd.DataFrame()
                n_ach = int(folds_total["target_achieved_inner"].sum()) if not folds_total.empty else 0
                n_all = len(folds_total)
                if sub.empty:
                    rows.append({"dataset": dom, "method": mth, "target": tag, "status": "not achieved (inner validation)",
                                 "folds_achieved": f"{n_ach}/{n_all}"})
                    continue
                s = MT.decision_metrics(sub)
                ci = MT.bootstrap_ci(sub, ["UAR", "coverage", "normalized_cost", "mean_acquisitions"], seed=SEED)
                status = "achieved" if n_ach == n_all else f"partially achieved ({n_ach}/{n_all} folds)"
                if kind == "uar":
                    status += "; held-out UAR meets target" if s["UAR"] <= t else "; held-out UAR exceeds target"
                rows.append({"dataset": dom, "method": mth, "target": tag, "status": status, "folds_achieved": f"{n_ach}/{n_all}",
                             "UAR": ci_str(s["UAR"], *ci["UAR"]), "coverage": ci_str(s["coverage"], *ci["coverage"]),
                             "normalized_cost": ci_str(s["normalized_cost"], *ci["normalized_cost"]),
                             "mean_acquisitions": ci_str(s["mean_acquisitions"], *ci["mean_acquisitions"]),
                             "expected_loss": fmt(s["expected_loss"]), "n_episodes": s["n"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------- calibration
def calibration_table(domains) -> pd.DataFrame:
    rows = []
    for exp, model in (("primary", "TAN"), ("model_lr", "Calibrated logistic")):
        for dom in domains:
            c = AD.table(exp, dom, "calib")
            if c.empty:
                continue
            for method, label in (("B0-AllEvidence", "all evidence acquired"), ("masked_random", "random evidence subsets"),
                                  ("AVOI-GRC", "AVOI terminal state (full trajectory)")):
                s = c[c["method"] == method]
                if s.empty:
                    continue
                m = MT.calibration_metrics(s["y"].to_numpy(), s["belief_full"].to_numpy())
                rows.append({"dataset": dom, "evidence_model": model, "evidence_state": label, "n": len(s), **m})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------- hypotheses
def evaluate_hypotheses(domains) -> pd.DataFrame:
    rows = []
    for dom in domains:
        df = AD.episodes("primary", dom)
        if df.empty:
            continue
        base = df[df["condition"] == AD.PRIMARY_COND]
        # ---------------- H1
        tests, details = [], []
        for t in (0.01, 0.02, 0.05):
            tag = f"target:uar<={t}"
            a = base[(base["method"] == "AVOI-GRC") & (base["shift"] == tag)]
            b = base[(base["method"] == "B1-FixedChecklist") & (base["shift"] == tag)]
            p = a.merge(b, on=["objective", "fold", "episode_id", "y"], suffixes=("_a", "_b"))
            if p.empty:
                details.append(f"UAR<={t}: not testable (target not achieved on inner validation by both methods in all folds)")
                continue
            w = MT.wilcoxon_paired(p["n_acq_a"], p["n_acq_b"])
            d, lo, hi = MT.paired_bootstrap_diff(p["n_acq_a"].to_numpy(float), p["n_acq_b"].to_numpy(float), p["y"].to_numpy(), seed=SEED)
            viol = (p["y"] == 0).to_numpy(float)
            ua = ((p["decision_a"] == "Assured") & (p["y"] == 0)).to_numpy(float)
            ub = ((p["decision_b"] == "Assured") & (p["y"] == 0)).to_numpy(float)
            du, ulo, uhi = MT.paired_bootstrap_diff(ua, ub, p["y"].to_numpy(), seed=SEED, denom=viol)
            tests.append({"target": t, "p": w["p"], "diff": d, "lo": lo, "hi": hi, "uar_diff_hi": uhi, "r": w["effect_rank_biserial"], "n": len(p),
                          "degenerate": bool(p["n_acq_a"].max() == 0 and p["n_acq_b"].max() == 0)})
        if tests:
            adj = MT.holm([x["p"] for x in tests])
            for x, pa in zip(tests, adj):
                x["p_holm"] = pa
                details.append(f"UAR<={x['target']}: mean acquisitions diff {x['diff']:.3f} [{x['lo']:.3f},{x['hi']:.3f}], "
                               f"Wilcoxon p_holm={pa:.4g}, r_rb={x['r']:.3f}, UAR diff upper bound {x['uar_diff_hi']:.3f} (n={x['n']})")
            t5 = [x for x in tests if x["target"] == 0.05]
            if t5:
                x = t5[0]
                sup = x["p_holm"] < 0.05 and x["hi"] < 0 and x["uar_diff_hi"] <= 0.02
                verdict = "supported" if sup else "not supported"
                if x["degenerate"]:
                    verdict = ("not supported - registered operating point degenerate (both methods selected thresholds that stop "
                               "at t=0 with zero acquisitions; see post-hoc deviation D1)")
            else:
                verdict = "not testable"
        else:
            verdict = "not testable"
        rows.append({"hypothesis": "H1", "dataset": dom, "verdict": verdict, "details": " | ".join(details)})
        # ---------------- H2
        bud = AD.table("primary", dom, "budget")
        det, tests = [], []
        for k in (1, 2, 3):
            a = bud[(bud["method"] == "AVOI-GRC") & (bud["budget"] == k) & (bud["condition"] == AD.PRIMARY_COND)]
            b = bud[(bud["method"] == "B4-InformationGain") & (bud["budget"] == k) & (bud["condition"] == AD.PRIMARY_COND)]
            p = a.merge(b, on=["objective", "fold", "episode_index", "y"], suffixes=("_a", "_b"))
            v = p["y"] == 0
            ua = (p["decision_a"] == "Assured") & v
            ub = (p["decision_b"] == "Assured") & v
            mc = MT.mcnemar_exact(ua[v].to_numpy(), ub[v].to_numpy())
            tests.append({"k": k, "p": mc["p"], "diff": float(ua[v].mean() - ub[v].mean()), "ua": ua.to_numpy(float),
                          "ub": ub.to_numpy(float), "viol": v.to_numpy(float), "y": p["y"].to_numpy()})
        adj = MT.holm([t["p"] for t in tests])
        ua_all = np.concatenate([t["ua"] for t in tests]); ub_all = np.concatenate([t["ub"] for t in tests])
        vi_all = np.concatenate([t["viol"] for t in tests]); y_all = np.concatenate([t["y"] for t in tests])
        est, lo, hi = MT.paired_bootstrap_diff(ua_all, ub_all, y_all, seed=SEED, denom=vi_all)
        for t, pa in zip(tests, adj):
            det.append(f"k={t['k']}: UAR diff {t['diff']:.4f}, McNemar p_holm={pa:.4g}")
        sig_better = any(pa < 0.05 and t["diff"] < 0 for t, pa in zip(tests, adj))
        sig_worse = any(pa < 0.05 and t["diff"] > 0 for t, pa in zip(tests, adj))
        verdict = "supported" if (hi < 0 and sig_better and not sig_worse) else "not supported"
        rows.append({"hypothesis": "H2", "dataset": dom, "verdict": verdict,
                     "details": f"summary UAR diff (k=1..3) {est:.4f} [{lo:.4f},{hi:.4f}] | " + " | ".join(det)})
        # ---------------- H3
        det, tests = [], []
        for cov in (0.6, 0.7, 0.8, 0.9):
            tag = f"target:coverage={cov}"
            a = base[(base["method"] == "AVOI-GRC") & (base["shift"] == tag)]
            b = base[(base["method"] == "B6-ConfidenceThreshold") & (base["shift"] == tag)]
            p = a.merge(b, on=["objective", "fold", "episode_id", "y"], suffixes=("_a", "_b"))
            if p.empty:
                det.append(f"coverage {cov}: not testable")
                continue
            v = p["y"] == 0
            mc = MT.mcnemar_exact(((p["decision_a"] == "Assured") & v)[v].to_numpy(), ((p["decision_b"] == "Assured") & v)[v].to_numpy())
            w = MT.wilcoxon_paired(p["n_acq_a"], p["n_acq_b"])
            tests.append({"cov": cov, "p": mc["p"], "pw": w["p"],
                          "duar": float(((p["decision_a"] == "Assured") & v)[v].mean() - ((p["decision_b"] == "Assured") & v)[v].mean()),
                          "dacq": float((p["n_acq_a"] - p["n_acq_b"]).mean()),
                          "cov_a": float((p["decision_a"] != "HumanReview").mean()), "cov_b": float((p["decision_b"] != "HumanReview").mean())})
        if tests:
            adj, adjw = MT.holm([t["p"] for t in tests]), MT.holm([t["pw"] for t in tests])
            better = sum(1 for t, pa in zip(tests, adj) if pa < 0.05 and t["duar"] < 0)
            worse = sum(1 for t, pa in zip(tests, adj) if pa < 0.05 and t["duar"] > 0)
            cheaper = sum(1 for t, pa, pw in zip(tests, adj, adjw) if pa >= 0.05 and pw < 0.05 and t["dacq"] < 0)
            for t, pa, pw in zip(tests, adj, adjw):
                det.append(f"coverage {t['cov']} (held-out {t['cov_a']:.2f} vs {t['cov_b']:.2f}): UAR diff {t['duar']:.4f} p_holm={pa:.4g}; "
                           f"acq diff {t['dacq']:.3f} p_holm={pw:.4g}")
            if better >= 2 and worse == 0:
                verdict = "supported"
            elif worse == 0 and cheaper >= 2:
                verdict = "supported via cost at equal safety"
            else:
                verdict = "not supported"
        else:
            verdict = "not testable"
        cur = AD.curves("primary", dom)
        if not cur.empty:
            det.append(f"AURC(UAR) AVOI={AD.aurc(AD.pooled_curve(cur, 'AVOI-GRC')):.4f}, B6={AD.aurc(AD.pooled_curve(cur, 'B6-ConfidenceThreshold')):.4f}")
        rows.append({"hypothesis": "H3", "dataset": dom, "verdict": verdict, "details": " | ".join(det)})
        # ---------------- H4
        det, tests = [], []
        for comp, exp in (("B5-GenericVOI", "primary"), ("A1-NoAsymmetricLoss", "ablation")):
            d2 = AD.tuned(exp, dom)
            if d2.empty:
                continue
            p = AD.paired_frame(d2, "AVOI-GRC", comp)
            v = p["y"] == 0
            ua, ub = ((p["decision_a"] == "Assured") & v)[v], ((p["decision_b"] == "Assured") & v)[v]
            mc = MT.mcnemar_exact(ua.to_numpy(), ub.to_numpy())
            tests.append({"comp": comp, "p": mc["p"], "diff": float(ua.mean() - ub.mean()), "b": mc["discordant_method_only"], "c": mc["discordant_comparator_only"]})
        adj = MT.holm([t["p"] for t in tests]) if tests else []
        for t, pa in zip(tests, adj):
            t["p_holm"] = pa
            det.append(f"vs {t['comp']}: UAR diff {t['diff']:.4f} (discordant {t['b']}/{t['c']}), McNemar p_holm={pa:.4g}")
        b5 = [t for t in tests if t["comp"] == "B5-GenericVOI"]
        a1 = [t for t in tests if t["comp"] == "A1-NoAsymmetricLoss"]
        if b5 and b5[0]["p_holm"] < 0.05 and b5[0]["diff"] < 0:
            verdict = "supported"
        elif a1 and a1[0]["p_holm"] < 0.05 and a1[0]["diff"] < 0:
            verdict = "partially supported (A1 only)"
        else:
            verdict = "not supported"
        rows.append({"hypothesis": "H4", "dataset": dom, "verdict": verdict, "details": " | ".join(det)})
        # ---------------- H5
        abl = AD.tuned("ablation", dom)
        det, tests = [], []
        if not abl.empty:
            p = AD.paired_frame(abl, "AVOI-GRC", "A6-NoEscalation")
            unsafe = lambda dcol: (((p[dcol] == "Assured") & (p["y"] == 0)) | ((p[dcol] == "NotAssured") & (p["y"] == 1)))
            subsets = {}
            prim = AD.tuned("primary", dom)
            if "conflict" in prim and dom == "iam":
                conf_ids = set(prim.loc[(prim["method"] == "AVOI-GRC") & (prim["conflict"] == True), "episode_id"])
                subsets["conflicting evidence"] = p["episode_id"].isin(conf_ids)
            b0 = prim[prim["method"] == "B0-AllEvidence"][["episode_id", "belief"]].rename(columns={"belief": "b_full"})
            tun = AD.table("primary", dom, "tuning")
            taus = tun[(tun["method"] == "AVOI-GRC") & (tun.get("chosen") == True) & (tun["condition"] == AD.PRIMARY_COND)][["objective", "fold", "tau"]]
            q = p.merge(b0, on="episode_id", how="left").merge(taus, on=["objective", "fold"], how="left")
            from avoi.bayes_risk import LossMatrix
            L = LossMatrix()
            subsets["insufficient evidence"] = (q["b_full"].map(L.risk) > q["tau"]).to_numpy()
            for name, mask in subsets.items():
                mask = np.asarray(mask, bool)
                if mask.sum() == 0:
                    det.append(f"{name}: empty subset")
                    continue
                ua, ub = unsafe("decision_a")[mask], unsafe("decision_b")[mask]
                mc = MT.mcnemar_exact(ua.to_numpy(), ub.to_numpy())
                tests.append({"subset": name, "p": mc["p"], "a": int(ua.sum()), "b": int(ub.sum()), "n": int(mask.sum()),
                              "uar_a": float(((p["decision_a"] == "Assured") & (p["y"] == 0))[mask].sum() / max(1, (p["y"] == 0)[mask].sum())),
                              "uar_b": float(((p["decision_b"] == "Assured") & (p["y"] == 0))[mask].sum() / max(1, (p["y"] == 0)[mask].sum()))})
            adj = MT.holm([t["p"] for t in tests]) if tests else []
            for t, pa in zip(tests, adj):
                t["p_holm"] = pa
                det.append(f"{t['subset']} (n={t['n']}): unsafe autonomous AVOI={t['a']} vs A6={t['b']}, UAR {t['uar_a']:.3f} vs {t['uar_b']:.3f}, McNemar p_holm={pa:.4g}")
            conf = [t for t in tests if t["subset"] == "conflicting evidence"]
            primary_subset = conf[0] if conf else ([t for t in tests if t["subset"] == "insufficient evidence"] or [None])[0]
            if primary_subset is None:
                verdict = "not testable"
            else:
                verdict = "supported" if (primary_subset["p_holm"] < 0.05 and primary_subset["a"] < primary_subset["b"]) else "not supported"
                if not conf:
                    verdict += " (no conflict subset in this domain; insufficient-evidence subset used)"
        else:
            verdict = "not testable"
        rows.append({"hypothesis": "H5", "dataset": dom, "verdict": verdict, "details": " | ".join(det)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------- provenance & objectives
def provenance_table() -> pd.DataFrame:
    man = json.loads((ROOT / "data" / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))["entries"]
    counts = {}
    for dom in AD.DOMAINS:
        try:
            from avoi.evaluation.runner import load_domain
            objs, labels = load_domain(dom)
            counts[dom] = {k: (v.n, int((labels[k] == 0).sum())) for k, v in objs.items()}
        except Exception:
            counts[dom] = {}
    usage = {
        "nist_oscal_content": ("SP 800-53 Rev.5 catalog/baselines", "0 (grounding only)", "not a label source", "n/a"),
        "nist_sp800_53a_r5_xlsx": ("AC/IA/AU/PS assessment objectives", "0 (grounding only)", "not a label source", "n/a"),
        "nist_sp800_53a_r5_csv": ("AC/IA/AU/PS assessment objectives", "0 (grounding only)", "not a label source", "n/a"),
        "nist_rmf_assessment_cases_ac": ("AC family assessment cases", "0 (grounding only)", "not a label source", "n/a"),
        "nist_rmf_assessment_cases_ia": ("IA family assessment cases", "0 (grounding only)", "not a label source", "n/a"),
        "nca_ecc_2_2024_en": ("ECC 1-9, 2-2 clauses", "0 (grounding only)", "not a label source", "n/a"),
        "nca_ecc_2_2024_ar": ("ECC (Arabic)", "0 (grounding only)", "not a label source", "n/a"),
        "nca_ecc_guide": ("IAM implementation guidance", "0 (grounding only)", "not a label source", "n/a"),
        "scf_2026_2": ("IAC controls, ERL, assessment objectives", "0 (grounding only)", "not a label source", "evidence-action vocabulary"),
        "botsv3": ("none (excluded)", "0", "official answer key e-mail gated", "AWS/host/network (not used)"),
        "cert_answers": ("r4.2 answer files", "ground truth for CERT", "answer key (labels only)", "n/a"),
        "cert_checksums": ("-", "-", "-", "-"),
        "cert_r4_2": ("250 sampled non-insiders + all 70 r4.2 insider instances", str(sum(n for n, _ in counts.get("cert", {}).values())),
                      "answer-key observable events per user-week", "logon, device, file, http, email, LDAP, psychometric"),
        "ait_lds_v2_russellmitchell": ("testbed russellmitchell, 10-min windows", str(counts.get("ait", {}).get("AIT-EXFIL", (0, 0))[0] // 2 * 2),
                                       "AIT line-level attack labels", "vpn, dns, apache, auth, audit, suricata, mail, syslog, monitoring"),
        "ait_lds_v2_santos": ("testbed santos, 10-min windows", "(included above; 2 claims x 1,152 windows)", "AIT line-level attack labels", "as above"),
        "lanl_cyber1": ("none (excluded)", "0", "red-team events (not obtained)", "auth, proc, flows, dns"),
    }
    rows = []
    for e in man:
        u = usage.get(e["id"], ("", "", "", ""))
        rows.append({"dataset": e["dataset"], "version": e.get("version"), "source": e.get("organization"), "DOI": e.get("doi") or "-",
                     "license": e.get("license"), "raw_size_bytes": e.get("size_bytes"), "status": e.get("status"),
                     "selected_subset": u[0], "n_episodes": u[1], "ground_truth_mechanism": u[2], "evidence_source_types": u[3],
                     "sha256": e.get("sha256") or "-", "checksum_verified": e.get("checksum_verified"),
                     "blocker": e.get("blocker") or ""})
    rows.append({"dataset": "Controlled IAM assurance testbed (this work)", "version": "generator 1.0 / Keycloak 26.3", "source": "this project",
                 "DOI": "-", "license": "project code", "raw_size_bytes": None, "status": "generated", "selected_subset": "320 scenarios x 6 objectives",
                 "n_episodes": str(sum(n for n, _ in counts.get("iam", {}).values())),
                 "ground_truth_mechanism": "oracle over live configuration/event store/host state", "evidence_source_types":
                 "policy docs, registers, tickets, HR feed, directory, config, reconciliation, auth/audit logs, host, login tests",
                 "sha256": json.loads((ROOT / "results" / "EXPERIMENT_FREEZE.json").read_text())["hashes"]["data"]["data/processed/iam/evidence_store/*.json"]["sha256"],
                 "checksum_verified": None, "blocker": ""})
    return pd.DataFrame(rows)


def objectives_table() -> pd.DataFrame:
    cfg = yaml.safe_load((ROOT / "config" / "assurance_objectives.yaml").read_text(encoding="utf-8"))
    rows = []
    for o in cfg["objectives"]:
        refs = o["framework_refs"]
        rows.append({"objective": o["id"], "framework_references": "; ".join(f"{k}: {', '.join(map(str, v))}" for k, v in refs.items()),
                     "operational_predicate": " ".join(o["operational_predicate"].split()),
                     "possible_actions": ", ".join(f"{a['id']} ({len(a['outcomes'])} outcomes)" for a in o["actions"]),
                     "ground_truth_source": o["ground_truth_source"]})
    from avoi.datasets.ait_episodes import FAM_ORDER
    from avoi.datasets.cert import ACTIONS
    rows.append({"objective": "AIT-EXFIL / AIT-INTRUSION (micro-claims)", "framework_references": "none (security-assurance micro-claim, not compliance)",
                 "operational_predicate": "no labelled DNS-exfiltration / intrusion-step activity in the 10-minute window",
                 "possible_actions": ", ".join(f"ait_query_{f}" for f in FAM_ORDER), "ground_truth_source": "AIT-LDS v2.0 labels/ files"})
    rows.append({"objective": "CERT-INSIDER (micro-claim)", "framework_references": "none (security-assurance micro-claim, not compliance)",
                 "operational_predicate": "no answer-key insider-scenario observable events for the user in the week",
                 "possible_actions": ", ".join(a[0] for a in ACTIONS), "ground_truth_source": "CERT r4.2 answer key"})
    return pd.DataFrame(rows)
