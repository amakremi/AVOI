"""Statistical analysis, tables, figures, failure analysis and final reports (all generated from saved raw results)."""
from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from common import ROOT, verify_freeze

from avoi.evaluation import analysis_data as AD
from avoi.evaluation import figures as FG
from avoi.evaluation import metrics as MT
from avoi.evaluation import reports as RP
from avoi.evaluation import stats_tables as ST

REPORT = ROOT / "results" / "final_report"


def llm_planner_table() -> pd.DataFrame:
    p = ROOT / "results" / "raw" / "llm_planner" / "episodes_llm_planner.csv.gz"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    rows = []
    for m, g in df.groupby("method"):
        s = MT.decision_metrics(g)
        ci = MT.bootstrap_ci(g, ["UAR", "expected_loss", "mean_acquisitions", "coverage"], seed=1)
        rows.append({"method": m, "n": s["n"], "UAR": ST.ci_str(s["UAR"], *ci["UAR"]), "expected_loss": ST.ci_str(s["expected_loss"], *ci["expected_loss"]),
                     "mean_acquisitions": ST.ci_str(s["mean_acquisitions"], *ci["mean_acquisitions"]),
                     "coverage": ST.ci_str(s["coverage"], *ci["coverage"]), "normalized_cost": s["normalized_cost"]})
    info = json.loads((ROOT / "results" / "raw" / "llm_planner" / "run_info.json").read_text())
    t = pd.DataFrame(rows)
    t["note"] = f"IAM outer fold 0 only; model {info['model']}; invalid responses {info['invalid_responses']}"
    return t


def num(domain, method, metric, experiment="primary"):
    x = AD.per_method(AD.tuned(experiment, domain), method)
    return MT.decision_metrics(x)[metric] if not x.empty else np.nan


def main():
    frozen = verify_freeze()
    REPORT.mkdir(parents=True, exist_ok=True)
    domains = [d for d in AD.DOMAINS if not AD.episodes("primary", d).empty]
    written = {}
    written["t1"] = ST.write_table(ST.provenance_table(), "table1_dataset_provenance", "Table 1. Dataset provenance")
    written["t2"] = ST.write_table(ST.objectives_table(), "table2_objectives_actions", "Table 2. Assurance objectives, micro-claims and evidence actions")
    t3, store = ST.main_table(domains)
    written["t3"] = ST.write_table(t3, "table3_main_comparison", "Table 3. Main method comparison (held-out, primary condition, 95% CI)")
    written["t4"] = ST.write_table(ST.target_table(domains, "coverage"), "table4_matched_coverage", "Table 4. Matched autonomous coverage (thresholds selected on inner validation)")
    written["t5"] = ST.write_table(ST.target_table(domains, "uar"), "table5_matched_safety", "Table 5. Matched safety level (lowest-cost threshold meeting UAR target on inner validation)")
    written["t6"] = ST.write_table(ST.calibration_table(domains), "table6_calibration", "Table 6. Calibration of evidence models (held-out)")
    written["t7"] = ST.write_table(RP.ablation_table(domains), "table7_ablation", "Table 7. Ablation study (held-out, primary condition, 95% CI)")
    stats = pd.concat([ST.paired_stats(d) for d in domains], ignore_index=True)
    abl_stats = pd.concat([ST.paired_stats(d, "ablation", [a for a in AD.ABLATIONS if a != "AVOI-GRC"]) for d in domains], ignore_index=True)
    fried = pd.DataFrame([{"dataset": d, **ST.friedman_table(d)} for d in domains])
    t8 = stats[["dataset", "comparison", "metric", "test", "statistic", "p", "p_holm"] +
               [c for c in stats.columns if c.startswith("effect")] + ["mean_difference", "ci_low", "ci_high", "n_pairs"]]
    written["t8"] = ST.write_table(t8, "table8_statistical_significance", "Table 8. AVOI-GRC vs baselines: paired tests (Holm-adjusted), effect sizes, 95% CI of differences")
    ST.write_table(abl_stats, "table8b_ablation_significance", "Table 8b. AVOI-GRC vs ablations: paired tests")
    ST.write_table(fried, "table8c_friedman_omnibus", "Table 8c. Friedman omnibus test across methods (blocks = objective x fold; metric = mean loss)")
    written["t9"] = ST.write_table(RP.generalization_table(domains, store), "table9_generalization", "Table 9. Dataset/domain generalisation")
    written["t10"] = ST.write_table(RP.sensitivity_table(domains), "table10_sensitivity", "Table 10. Sensitivity analysis")
    from avoi.evaluation import posthoc as PH
    t5b, h1_posthoc = PH.safety_table_nondegenerate(domains)
    written["t5b"] = ST.write_table(t5b, "table5b_matched_safety_nondegenerate", "Table 5b. POST-HOC (deviation D1): matched safety excluding operating points worse than escalate-all (inner J <= 1)")
    ST.write_table(h1_posthoc, "table11b_h1_posthoc", "Table 11b. POST-HOC (deviation D1): H1 with non-degenerate safety matching")
    hyp = ST.evaluate_hypotheses(domains)
    ST.write_table(hyp, "table11_hypotheses", "Table 11. Pre-registered hypotheses H1-H5")
    llm = llm_planner_table()
    if not llm.empty:
        ST.write_table(llm, "table12_llm_planner", "Table 12. Secondary: LLM-only planner (B8) vs AVOI-GRC on a predefined subset")
    # cross-dataset: per-dataset effects; meta-analysis only if >= 3 compatible PUBLIC datasets
    public = [d for d in domains if d != "iam"]
    eff = stats[(stats["metric"] == "expected_loss")]
    meta_note = (f"Random-effects meta-analysis NOT performed: only {len(public)} public datasets (AIT, CERT) were available; the "
                 "protocol requires at least three compatible public datasets.") if len(public) < 3 else ""
    figs = FG.all_figures()
    fail = RP.failure_analysis(domains)
    (REPORT / "FAILURE_ANALYSIS.md").write_text(fail, encoding="utf-8")
    claims = RP.classify_claims(stats, domains, hyp)

    # ------------------------------------------------------------------ RESULTS.md
    L = []
    L += ["# AVOI-GRC — experimental results (auto-generated)", "",
          f"Frozen configuration SHA-256: `{frozen['hashes']['combined_sha256']}` (frozen {frozen['frozen_utc']}).",
          "All numbers are computed from `results/raw` by `experiments/run_statistics.py`. Held-out episodes only; 95% CIs are "
          "stratified bootstrap percentile intervals (5,000 resamples). Layer A = controlled IAM testbed (objective-level ground "
          "truth); Layer B = public replay micro-claims (AIT-LDS v2.0, CERT r4.2) — NOT compliance decisions.", ""]
    L += ["## Datasets and episodes", ""]
    for d in domains:
        objs, labels = __import__("avoi.evaluation.runner", fromlist=["load_domain"]).load_domain(d)
        L.append(f"- {AD.DOMAIN_LABEL[d]}: " + "; ".join(f"{k}: {v.n} episodes ({int((labels[k] == 0).sum())} violated/refuted), "
                                                           f"{v.m} actions" for k, v in objs.items()))
    L += ["- Excluded: Splunk BOTS v3 (answer key e-mail gated; proprietary index format), LANL cyber1 (e-mail form gated).", ""]
    L += ["## RQ1 — Acquisition efficiency", ""]
    for d in domains:
        a = store.get((d, "AVOI-GRC"), {})
        if not a:
            continue
        L.append(f"**{AD.DOMAIN_LABEL[d]}** — AVOI-GRC: mean acquisitions {a['mean_acquisitions']:.3f} "
                 f"[{a['ci']['mean_acquisitions'][0]:.3f}, {a['ci']['mean_acquisitions'][1]:.3f}], normalised cost {a['normalized_cost']:.4f} "
                 f"[{a['ci']['normalized_cost'][0]:.4f}, {a['ci']['normalized_cost'][1]:.4f}], expected loss {a['expected_loss']:.4f}.")
        L.append("- Paired difference in acquisitions (AVOI − baseline):")
        L += RP.comparison_sentences(stats, d, "acquisitions")
        L.append("- Paired difference in normalised cost (AVOI − baseline):")
        L += RP.comparison_sentences(stats, d, "normalized_cost")
        L.append("")
    L += ["## RQ2 — Assurance safety", ""]
    for d in domains:
        a = store.get((d, "AVOI-GRC"), {})
        if not a:
            continue
        L.append(f"**{AD.DOMAIN_LABEL[d]}** — AVOI-GRC UAR {a['UAR']:.4f} [{a['ci']['UAR'][0]:.4f}, {a['ci']['UAR'][1]:.4f}], "
                 f"FAR among approvals {a['FAR_A']:.4f}, expected loss {a['expected_loss']:.4f} [{a['ci']['expected_loss'][0]:.4f}, "
                 f"{a['ci']['expected_loss'][1]:.4f}].")
        L.append("- Absolute UAR difference (AVOI − baseline); relative difference in parentheses:")
        s = stats[(stats["dataset"] == d) & (stats["metric"] == "UAR")]
        for r in s.itertuples():
            comp = r.comparison.split(" vs ")[1]
            base = store.get((d, comp), {}).get("UAR", np.nan)
            rel = (r.mean_difference / base) if base and not np.isnan(base) and base > 0 else np.nan
            L.append(f"  - vs {comp} (UAR {base:.4f}): {r.mean_difference:+.4f} [{r.ci_low:+.4f}, {r.ci_high:+.4f}] "
                     f"(relative {rel:+.1%}); {r.test} p={r.p:.3g}, Holm p={r.p_holm:.3g}" if not np.isnan(rel) else
                     f"  - vs {comp} (UAR {base:.4f}): {r.mean_difference:+.4f} [{r.ci_low:+.4f}, {r.ci_high:+.4f}]; {r.test} p={r.p:.3g}, Holm p={r.p_holm:.3g}")
        L.append("- Expected decision loss difference (AVOI − baseline):")
        L += RP.comparison_sentences(stats, d, "expected_loss")
        L.append("")
    L += ["## RQ3 — Governed autonomy (risk–coverage / escalation)", ""]
    for d in domains:
        cur = AD.curves("primary", d)
        au = {m: AD.aurc(AD.pooled_curve(cur, m)) for m in ["AVOI-GRC", "B1-FixedChecklist", "B3-CheapestFirst", "B4-InformationGain",
                                                            "B6-ConfidenceThreshold", "B7b-Lookahead2VOI", "B2-Random"]}
        a = store.get((d, "AVOI-GRC"), {})
        L.append(f"**{AD.DOMAIN_LABEL[d]}** — area under the UAR–coverage curve (lower is better): " +
                 ", ".join(f"{k} {v:.4f}" for k, v in au.items()) +
                 f". AVOI-GRC at its tuned threshold: coverage {a.get('coverage', np.nan):.3f}, escalation rate {a.get('escalation_rate', np.nan):.3f}. "
                 "Single-point methods without escalation (B5, B7) have coverage 1 by construction: "
                 f"B5 UAR {store.get((d, 'B5-GenericVOI'), {}).get('UAR', np.nan):.4f}, B7 UAR {store.get((d, 'B7-MyopicCostSensitiveVOI'), {}).get('UAR', np.nan):.4f}.")
        t4 = pd.read_csv(ROOT / "results" / "tables" / "table4_matched_coverage.csv")
        sub = t4[(t4["dataset"] == d) & (t4["method"].isin(["AVOI-GRC", "B6-ConfidenceThreshold", "B1-FixedChecklist", "B4-InformationGain"]))]
        for r in sub.itertuples():
            L.append(f"  - {r.method} {r.target}: {r.status}; UAR {getattr(r, 'UAR', 'n/a')}; coverage {getattr(r, 'coverage', 'n/a')}; "
                     f"acquisitions {getattr(r, 'mean_acquisitions', 'n/a')}")
        L.append("")
    # ------------------------------------------------------------------ conservative interpretation (computed)
    L += ["## Conservative interpretation (computed from Table 8)", ""]
    for d in domains:
        s = stats[stats["dataset"] == d]
        def sig(metric, direction):
            rows = s[(s["metric"] == metric) & (s["p_holm"] < 0.05) & ((s["ci_high"] < 0) if direction == "lower" else (s["ci_low"] > 0))]
            return ", ".join(r.split(" vs ")[1] for r in rows["comparison"]) or "none"
        L.append(f"- **{d}**: AVOI-GRC expected loss significantly LOWER than [{sig('expected_loss', 'lower')}] and significantly HIGHER "
                 f"than [{sig('expected_loss', 'higher')}]; UAR significantly lower than [{sig('UAR', 'lower')}], higher than "
                 f"[{sig('UAR', 'higher')}]; acquisitions significantly fewer than [{sig('acquisitions', 'lower')}], more than "
                 f"[{sig('acquisitions', 'higher')}].")
    abl_iam = AD.tuned("ablation", "iam")
    prim_iam = AD.tuned("primary", "iam")
    if not abl_iam.empty and "conflict" in prim_iam:
        conf = set(prim_iam.loc[(prim_iam["method"] == "AVOI-GRC") & (prim_iam["conflict"] == True), "episode_id"])
        p = AD.paired_frame(abl_iam, "AVOI-GRC", "A6-NoEscalation")
        p = p[p["episode_id"].isin(conf)]
        v = p["y"] == 0
        fa_a, fa_b = int(((p["decision_a"] == "Assured") & v).sum()), int(((p["decision_b"] == "Assured") & v).sum())
        fn_a = int(((p["decision_a"] == "NotAssured") & ~v).sum())
        fn_b = int(((p["decision_b"] == "NotAssured") & ~v).sum())
        mc = MT.mcnemar_exact(((p["decision_a"] == "Assured") & v)[v].to_numpy(), ((p["decision_b"] == "Assured") & v)[v].to_numpy())
        L.append(f"- **H5 caveat (IAM conflicting-evidence subset, n={len(p)})**: false assurances AVOI {fa_a} vs A6 {fa_b} "
                 f"(exact McNemar p={mc['p']:.3g}); false non-assurances AVOI {fn_a} vs A6 {fn_b}. Escalation reduced unsafe "
                 "autonomous decisions mainly by avoiding false NON-assurance; it did not reduce false assurance relative to the "
                 "no-escalation variant, which (under the 10:2 loss) defaults to NotAssured when uncertain.")
    if not llm.empty:
        L.append("- **LLM planner**: see the secondary section; llama3.1:8b acquired almost every available evidence item, so its loss "
                 "is not comparable to an efficient planner at equal acquisition budget.")
    L.append("- **AIT**: the TAN evidence model transfers poorly between the two testbeds (full-evidence ECE in Table 6); all methods share "
             "this model, so AIT results mostly reflect cross-testbed distribution shift rather than acquisition policy differences. "
             "AIT-INTRUSION has only 12 refuted windows.")
    L.append("")
    L += ["## Deviations from the pre-registration", "",
          "- **D1 (post-hoc, declared here):** the registered safety-target selection (lowest inner cost with inner UAR <= target) is "
          "satisfied trivially by thresholds that stop at t=0 and decide NotAssured for every episode (UAR does not penalise false "
          "non-assurance). Registered H1 and Table 5 are reported unchanged; Table 5b / Table 11b add a non-degenerate variant "
          "(additionally requiring inner tuning objective J <= 1.0, the value of escalating every episode). Post-hoc results "
          "cannot confirm the pre-registered hypothesis and are labelled exploratory.", ""]
    if not h1_posthoc.empty:
        L += ["Post-hoc H1 (non-degenerate matching, AVOI-GRC vs B1-FixedChecklist):"]
        for r in h1_posthoc.to_dict("records"):
            if not pd.isna(r.get("acq_diff", np.nan)):
                L.append(f"- {r['dataset']} UAR<={r['target']}: acquisitions {r['mean_acq_AVOI']:.3f} vs {r['mean_acq_B1']:.3f}, diff "
                         f"{r['acq_diff']:+.3f} [{r['acq_ci_low']:+.3f}, {r['acq_ci_high']:+.3f}], Wilcoxon Holm p={r['p_holm']:.3g}, "
                         f"rank-biserial {r['rank_biserial']:.3f}; UAR diff {r['uar_diff']:+.4f} [{r['uar_ci_low']:+.4f}, "
                         f"{r['uar_ci_high']:+.4f}] (n={r['n_pairs']}) -> {r['verdict_posthoc']} (exploratory)")
            else:
                L.append(f"- {r['dataset']} UAR<={r['target']}: {r.get('result', 'not testable')}")
        L.append("")
    L += ["## Pre-registered hypotheses", ""] + [f"- **{r.hypothesis} ({r.dataset})**: {r.verdict}. {r.details}" for r in hyp.itertuples()] + [""]
    L += ["## Ablations (AVOI − ablation, expected loss and UAR)", ""]
    for d in domains:
        for metric in ("expected_loss", "UAR"):
            L.append(f"- {d} / {metric}:")
            L += RP.comparison_sentences(abl_stats, d, metric)
    L += ["", "## Omnibus tests", ""] + [f"- {r.dataset}: Friedman χ²={r.statistic:.3f}, p={r.p:.3g}, blocks={r.n_blocks}, methods={r.k}, "
                                            f"Kendall W={getattr(r, 'effect_kendall_w', float('nan')):.3f}" for r in fried.itertuples()]
    L += ["", "## Cross-dataset summary", "", meta_note or "Meta-analysis performed (see table).",
          "Per-dataset effects are reported separately; the macro-average rows in Table 3 average dataset-level estimates and "
          "do not pool raw episodes.", ""]
    if not llm.empty:
        L += ["## Secondary: LLM-only planner", ""] + [f"- {r.method}: UAR {r.UAR}; loss {r.expected_loss}; acquisitions {r.mean_acquisitions}; "
                                                        f"coverage {r.coverage} ({r.note})" for r in llm.itertuples()] + [""]
    L += ["## Generated artefacts", ""] + [f"- {v['csv']} (+ .md, .tex)" for v in written.values()]
    L += [f"- {p}" for ps in figs.values() for p in ps]
    (REPORT / "RESULTS.md").write_text("\n".join(L), encoding="utf-8")

    # ------------------------------------------------------------------ CLAIMS_ALLOWED.md
    C = ["# Claims allowed by the held-out results (auto-generated, conservative rules)", "",
         "Rule: a claim is **supported** only when the paired comparison is statistically significant after Holm correction "
         "(p < 0.05) with a 95% CI excluding zero in the favourable direction on EVERY evaluated dataset; **partially supported** "
         "when this holds on some datasets only; otherwise **unsupported**. Statistical significance is not practical superiority; "
         "effect sizes are in Table 8.", "", "## Supported claims", ""]
    C += [f"- {c}" for c in claims["supported"]] or ["- (none)"]
    C += ["", "### Required context for the supported claims", ""] + ([f"- {c}" for c in claims["context"]] or ["- (none)"])
    C += ["", "## Partially supported claims", ""] + ([f"- {c}" for c in claims["partial"]] or ["- (none)"])
    C += ["", "## Unsupported claims", ""] + [f"- {c}" for c in claims["unsupported"]]
    (REPORT / "CLAIMS_ALLOWED.md").write_text("\n".join(C), encoding="utf-8")

    # ------------------------------------------------------------------ PAPER_RESULTS.tex
    T = [r"% Auto-generated by experiments/run_statistics.py — do not edit numbers by hand", r"\section{Results}"]
    for d in domains:
        a = store.get((d, "AVOI-GRC"), {})
        if a:
            T.append(rf"\paragraph{{{AD.DOMAIN_LABEL[d]}}} AVOI-GRC reached an unsafe assurance rate of {a['UAR']:.3f} "
                     rf"(95\% CI {a['ci']['UAR'][0]:.3f}--{a['ci']['UAR'][1]:.3f}), expected loss {a['expected_loss']:.3f} "
                     rf"({a['ci']['expected_loss'][0]:.3f}--{a['ci']['expected_loss'][1]:.3f}), {a['mean_acquisitions']:.2f} acquisitions "
                     rf"per episode and autonomous coverage {a['coverage']:.3f}.")
    T.append(r"\paragraph{Hypotheses} " + " ".join(rf"{r.hypothesis} ({r.dataset}): {r.verdict}." for r in hyp.itertuples()))
    for key in ("t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10"):
        T.append(rf"\input{{../tables/{Path(written[key]['tex']).name}}}")
    (REPORT / "PAPER_RESULTS.tex").write_text("\n".join(T).replace("%", r"\%").replace(r"\\%", r"\%").replace(r"\% Auto", "% Auto"), encoding="utf-8")

    summary = {"domains": domains, "tables": {k: v["csv"] for k, v in written.items()}, "figures": figs,
               "hypotheses": hyp[["hypothesis", "dataset", "verdict"]].to_dict("records"),
               "avoi": {d: {k: store[(d, "AVOI-GRC")][k] for k in ("UAR", "expected_loss", "mean_acquisitions", "normalized_cost", "coverage")}
                        for d in domains if (d, "AVOI-GRC") in store}}
    for d in domains:
        cands = {m: store[(d, m)]["expected_loss"] for m in RP.BASELINES if (d, m) in store}
        summary.setdefault("strongest_baseline_by_expected_loss", {})[d] = min(cands, key=cands.get) if cands else None
    (REPORT / "summary.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=float))


if __name__ == "__main__":
    main()
