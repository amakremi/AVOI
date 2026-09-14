"""Remaining tables (7, 9, 10), failure analysis and generated reports (RESULTS.md, PAPER_RESULTS.tex, CLAIMS_ALLOWED.md,
FAILURE_ANALYSIS.md). Every number is computed from results/raw and results/traces."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from avoi.bayes_risk import LossMatrix
from avoi.evaluation import analysis_data as AD
from avoi.evaluation import metrics as MT
from avoi.evaluation import stats_tables as ST

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "results" / "final_report"
BASELINES = ["B0-AllEvidence", "B1-FixedChecklist", "B2-Random", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI",
             "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI", "B7b-Lookahead2VOI"]
POL = {"supports_satisfied": 1, "supports_violated": -1, "neutral": 0}


# ---------------------------------------------------------------------------------------------- tables 7, 9, 10
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


# ---------------------------------------------------------------------------------------------- failure analysis
def render_trace(tr: dict, max_steps: int = 8) -> str:
    op = tr["operating_point"]
    lines = [f"- episode `{tr['episode_id']}` — true Y={tr['y']} — decision **{op['decision']}** after {op['n_acquisitions']} "
             f"acquisitions (stop: {op['reason']}; tuned τ={tr['tuned_threshold']}); initial belief {tr['initial_belief']:.3f}"]
    for s in tr["steps"][: min(op["n_acquisitions"], max_steps)]:
        best = sorted(s.get("candidates", []), key=lambda c: -c["value"])[:2]
        alt = "; ".join(f"{tr_action(tr, c['action'])} AVOI={c['value']:.3f}" for c in best)
        lines.append(f"  - t={s['t']}: `{s['selected_action']}` → `{s['observed_outcome']}`; belief {s['updated_belief']:.3f}, "
                     f"risk {s['updated_risk']:.3f} (top candidates: {alt})")
    return "\n".join(lines)


def tr_action(tr, idx):
    for s in tr["steps"]:
        if s["action_index"] == idx:
            return s["selected_action"]
    return f"action#{idx}"


def failure_analysis(domains) -> str:
    out = ["# Failure analysis (generated from held-out traces and episode records)", "",
           "All counts refer to AVOI-GRC at its inner-tuned threshold in the primary condition unless stated otherwise. "
           "Traces are reproduced verbatim from `results/traces/`.", ""]
    obj_cfg = yaml.safe_load((ROOT / "config" / "assurance_objectives.yaml").read_text(encoding="utf-8"))
    polar = {a["id"]: {o: POL[p] for o, p in a["outcomes"].items()} for o in obj_cfg["objectives"] for a in o["actions"]}
    cat = yaml.safe_load((ROOT / "config" / "evidence_actions.yaml").read_text(encoding="utf-8"))["iam_actions"]
    L = LossMatrix()
    for dom in domains:
        traces = AD.load_traces(dom, "AVOI-GRC")
        if not traces:
            continue
        df = AD.tuned("primary", dom)
        out += [f"## {AD.DOMAIN_LABEL[dom]}", ""]
        fa = [t for t in traces if t["operating_point"]["decision"] == "Assured" and t["y"] == 0]
        fna = [t for t in traces if t["operating_point"]["decision"] == "NotAssured" and t["y"] == 1]
        hr = [t for t in traces if t["operating_point"]["decision"] == "HumanReview"]
        n = len(traces)
        out.append(f"### False assurances ({len(fa)} of {n} episodes; {sum(t['y'] == 0 for t in traces)} violated)")
        if fa:
            by_obj = pd.Series([t["objective_id"] for t in fa]).value_counts()
            out.append("By objective/claim: " + ", ".join(f"{k}: {v}" for k, v in by_obj.items()))
            conf = [t for t in fa if t["operating_point"]["belief"] >= 0.95]
            out.append(f"Over-confident false assurances (terminal belief ≥ 0.95): {len(conf)} — these are calibration/model failures "
                       "rather than acquisition-order failures.")
            if dom == "iam":
                doc = 0
                for t in fa:
                    k = t["operating_point"]["n_acquisitions"]
                    if any(cat[s["selected_action"]]["source_type"] in ("policy_document", "register_record", "ticket_record")
                           and polar[s["selected_action"]].get(s["observed_outcome"], 0) == 1 for s in t["steps"][:k]):
                        doc += 1
                out.append(f"False assurances whose acquired evidence included documentary evidence nominally supporting satisfaction "
                           f"(evidence-source reliability failure pattern): {doc}")
            out += ["", "Representative traces:"] + [render_trace(t) for t in fa[:3]]
        out += ["", f"### False non-assurances ({len(fna)} episodes)"]
        if fna:
            out += [render_trace(t) for t in fna[:2]]
        # unnecessary escalations: full evidence would have allowed a correct autonomous decision under tau
        b0 = df[df["method"] == "B0-AllEvidence"].set_index("episode_id")["belief"]
        unnecessary = []
        for t in hr:
            bf = b0.get(t["episode_id"])
            if bf is None:
                continue
            correct_auto = (L.autonomous_decision(bf) == "Assured") == (t["y"] == 1)
            if L.risk(bf) <= (t["tuned_threshold"] or 0) and correct_auto:
                unnecessary.append(t)
        out += ["", f"### Escalations: {len(hr)} HumanReview decisions; {len(unnecessary)} were unnecessary in the sense that the "
                "complete available evidence would have supported a correct autonomous decision under the same threshold "
                "(AVOI stopped because the expected value of the remaining evidence did not exceed its cost/privacy/delay terms)."]
        out += [render_trace(t) for t in unnecessary[:2]]
        costs = sorted(traces, key=lambda t: -t["operating_point"]["cost"])
        k = max(1, n // 100)
        out += ["", f"### Most expensive acquisition sequences (top 1%: {k} episodes)"]
        out += [render_trace(t, 10) + f" — cost {t['operating_point']['cost']:.3f}" for t in costs[: min(k, 3)]]
        for comp in ("B4-InformationGain", "B5-GenericVOI"):
            p = AD.paired_frame(df, "AVOI-GRC", comp)
            better = p[p["loss_b"] < p["loss_a"]]
            worse = p[p["loss_b"] > p["loss_a"]]
            out += ["", f"### Episodes where {comp} beat AVOI-GRC on realised loss: {len(better)} (AVOI better: {len(worse)}; ties: "
                    f"{len(p) - len(better) - len(worse)})"]
            if len(better):
                ids = set(better["episode_id"].head(2))
                out += [render_trace(t) for t in traces if t["episode_id"] in ids][:2]
                out.append(f"Decision patterns in these episodes (AVOI → {comp}): " + ", ".join(
                    f"{a}→{b}: {c}" for (a, b), c in better.groupby(["decision_a", "decision_b"]).size().items()))
        cal = AD.table("primary", dom, "calib")
        if not cal.empty:
            s = cal[cal["method"] == "B0-AllEvidence"]
            m = MT.calibration_metrics(s["y"].to_numpy(), s["belief_full"].to_numpy())
            out += ["", f"### Calibration: full-evidence TAN posterior Brier {m['Brier']:.3f}, ECE {m['ECE']:.3f}, "
                    f"slope {m['calibration_slope']:.2f}, intercept {m['calibration_intercept']:.2f}. A slope < 1 indicates "
                    "over-confident posteriors, which directly causes threshold-based stopping to accept too early."]
        abl = AD.tuned("ablation", dom)
        if not abl.empty:
            p = AD.paired_frame(abl, "AVOI-GRC", "A8-NaiveBayesModel")
            tan_wrong = p[(p["loss_a"] > p["loss_b"])]
            nb_wrong = p[(p["loss_b"] > p["loss_a"])]
            out += ["", f"### Conditional-dependence modelling: TAN vs Naive Bayes (A8) realised loss — TAN worse in {len(tan_wrong)} "
                    f"episodes, NB worse in {len(nb_wrong)} episodes (mean loss TAN {p['loss_a'].mean():.3f} vs NB {p['loss_b'].mean():.3f})."]
        prim = AD.episodes("primary", dom)
        prim = prim[prim["condition"] == AD.PRIMARY_COND]
        coldrows = prim[(prim["shift"] == "none") & (prim["start"] == "cold") & (prim["method"] == "AVOI-GRC")]
        degrows = prim[prim["shift"].str.startswith("degrade") & (prim["method"] == "AVOI-GRC")]
        items = []
        for sh, g in degrows.groupby("shift"):
            base = coldrows[coldrows["episode_id"].isin(set(g["episode_id"]))]["loss"].mean()   # same episodes (source type may exist in some objectives only)
            items.append((sh.split(":")[1], g["loss"].mean(), base, g["episode_id"].nunique()))
        if items:
            out += ["", "### Distribution-shift failures (reliability of one source category degraded at evaluation, no retraining)",
                    "Loss under degradation vs cold-start loss on the SAME episodes (the source category may exist only for some objectives): " +
                    ", ".join(f"{s} {v:.3f} vs {b:.3f} (Δ {v - b:+.3f}, n={n})" for s, v, b, n in sorted(items, key=lambda t: -(t[1] - t[2]))),
                    "Negative Δ (degradation improving loss) indicates that the degraded source was misleading for the fitted model on "
                    "held-out data (e.g. under cross-testbed shift), not that degradation is beneficial in general."]
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------- reports
def direction_word(diff, lower_is_better=True):
    return "lower" if diff < 0 else "higher"


def comparison_sentences(stats: pd.DataFrame, dom: str, metric: str, unit: str = "") -> list[str]:
    s = stats[(stats["dataset"] == dom) & (stats["metric"] == metric)]
    lines = []
    for r in s.itertuples():
        comp = r.comparison.split(" vs ")[1]
        if r.p_holm < 0.05 and (r.ci_high < 0 or r.ci_low > 0):
            sig = "statistically significant"
        elif r.p_holm < 0.05:
            sig = "inconclusive: significant paired test but the 95% CI of the mean difference includes 0"
        elif r.ci_high < 0 or r.ci_low > 0:
            sig = "inconclusive: CI excludes 0 but the Holm-adjusted test is not significant"
        else:
            sig = "not statistically significant"
        lines.append(f"  - vs {comp}: difference {r.mean_difference:+.4f}{unit} [95% CI {r.ci_low:+.4f}, {r.ci_high:+.4f}], "
                     f"{r.test} p={r.p:.3g}, Holm p={r.p_holm:.3g} ({sig})")
    return lines


def classify_claims(stats: pd.DataFrame, domains, hyp: pd.DataFrame) -> dict:
    cats = {"supported": [], "partial": [], "unsupported": []}
    for metric, desc in (("expected_loss", "lower expected decision loss"), ("UAR", "lower unsafe assurance rate"),
                         ("acquisitions", "fewer evidence acquisitions"), ("normalized_cost", "lower normalised acquisition cost"),
                         ("privacy_exposure", "lower privacy exposure")):
        for comp in BASELINES:
            fav, unfav, tested = [], [], []
            for dom in domains:
                r = stats[(stats["dataset"] == dom) & (stats["metric"] == metric) & (stats["comparison"] == f"AVOI-GRC vs {comp}")]
                if r.empty:
                    continue
                r = r.iloc[0]
                tested.append(dom)
                if r.p_holm < 0.05 and r.ci_high < 0:
                    fav.append(f"{dom} ({r.mean_difference:+.4f} [{r.ci_low:+.4f}, {r.ci_high:+.4f}])")
                elif r.p_holm < 0.05 and r.ci_low > 0:
                    unfav.append(f"{dom} ({r.mean_difference:+.4f} [{r.ci_low:+.4f}, {r.ci_high:+.4f}])")
            if not tested:
                continue
            claim = f"AVOI-GRC achieves {desc} than {comp}"
            if fav and len(fav) == len(tested):
                cats["supported"].append(f"{claim} on every evaluated dataset: " + "; ".join(fav))
            elif fav:
                cats["partial"].append(f"{claim}: significant in " + "; ".join(fav) +
                                       (f"; significantly WORSE in " + "; ".join(unfav) if unfav else "") +
                                       f"; not significant elsewhere among {', '.join(tested)}")
            else:
                cats["unsupported"].append(f"{claim}" + (f" (significantly worse in " + "; ".join(unfav) + ")" if unfav else
                                                         " (no dataset shows a significant improvement)"))
    for r in hyp.itertuples():
        text = f"{r.hypothesis} on {r.dataset}: {r.verdict}"
        if r.hypothesis == "H5" and r.verdict.startswith("supported"):
            text += (" — CAVEAT: the registered outcome counts unsafe AUTONOMOUS decisions (false assurance + false non-assurance); "
                     "see RESULTS.md for whether escalation also lowered the false-assurance rate itself")
        if r.verdict == "supported" and r.hypothesis != "H5":
            cats["supported"].append(text)
        elif r.verdict == "supported" and r.hypothesis == "H5" and r.dataset == "iam":
            cats["supported"].append(text)
        elif r.verdict.startswith(("partially", "supported")):
            cats["partial"].append(text)
        else:
            cats["unsupported"].append(text)
    # context for efficiency claims: fewer acquisitions/cost while expected loss is significantly worse
    worse_loss = {}
    for comp in BASELINES:
        for dom in domains:
            r = stats[(stats["dataset"] == dom) & (stats["metric"] == "expected_loss") & (stats["comparison"] == f"AVOI-GRC vs {comp}")]
            if not r.empty and r.iloc[0].p_holm < 0.05 and r.iloc[0].ci_low > 0:
                worse_loss.setdefault(comp, []).append(f"{dom} (+{r.iloc[0].mean_difference:.4f})")
    cats["context"] = [f"Efficiency claims versus {comp} must be read together with AVOI-GRC's significantly HIGHER expected decision "
                       f"loss in: {', '.join(v)}." for comp, v in worse_loss.items()]
    cats["unsupported"] += [
        "AVOI-GRC automates or certifies regulatory compliance (NCA ECC, NIST, ISO): no compliance decision was evaluated; "
        "testbed predicates are experimental operationalisations and public-dataset labels are attack/insider micro-claims.",
        "AVOI-GRC outperforms human auditors: no human study was performed.",
        "AVOI-GRC yields real organisational audit cost savings: costs are testbed/replay measurements (records, bytes, seconds).",
        "Results generalise to real enterprise organisations: the IAM testbed is synthetic-but-live and the public corpora are testbed/"
        "synthetic datasets.",
        "Privacy exposure reductions correspond to reduced privacy risk: the exposure metric is a category-count proxy.",
        "Results hold for BOTS v3 or LANL: these datasets were not evaluated (access blockers documented).",
    ]
    all_sup = all(any(f"than {b} on every evaluated dataset" in s for s in cats["supported"] if "expected decision loss" in s)
                  for b in BASELINES)
    if not all_sup:
        cats["unsupported"].append("\"AVOI-GRC outperforms all baselines\" (expected loss): not established on every dataset for every baseline.")
    return cats
