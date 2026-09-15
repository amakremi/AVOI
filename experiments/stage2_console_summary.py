"""Final console summary (Stage 1 + Stage 2). Reads frozen files and generated tables only."""
from __future__ import annotations

import json

import pandas as pd

from common import ROOT

S1 = ROOT / "results" / "stage1_ungated"
S2 = ROOT / "results" / "stage2"
T = S2 / "tables"


def main():
    p = print
    s1 = json.loads((S1 / "manuscript" / "final_report" / "summary.json").read_text(encoding="utf-8"))
    fr1 = json.loads((S1 / "EXPERIMENT_FREEZE.json").read_text(encoding="utf-8"))
    fr2 = json.loads((S2 / "EXPERIMENT_FREEZE_STAGE2.json").read_text(encoding="utf-8"))
    dec = json.loads((S2 / "ADEQUACY_DECISIONS.json").read_text(encoding="utf-8"))
    p("=" * 100); p("STAGE 1 (original, ungated; historical)"); p("=" * 100)
    p(f"archive: {S1.relative_to(ROOT)}   original freeze sha256: {fr1['hashes']['combined_sha256']}")
    for d, v in s1["avoi"].items():
        p(f"  AVOI {d:5s} UAR {v['UAR']:.3f}  loss {v['expected_loss']:.3f}  acquisitions {v['mean_acquisitions']:.2f}  coverage {v['coverage']:.3f}"
          f"  (strongest baseline by loss: {s1['strongest_baseline_by_expected_loss'][d]})")
    for h in s1["hypotheses"]:
        p(f"  {h['hypothesis']} [{h['dataset']}]: {h['verdict']}")
    p("=" * 100); p("STAGE 2 (evidence-model adequacy safety condition + confirmation)"); p("=" * 100)
    p(f"Stage-2 freeze sha256: {fr2['hashes']['combined_sha256']}   adequacy decisions sha256: {dec['decisions_sha256']}")
    p("new IAM scenarios: 320 (seed 20261103); validation families 0-15 (128), confirmation families 16-39 (192 scenarios, 1,152 episodes)")
    p("external partitions: AIT-LDS v2.0 fox (validation) / harrison+wardbeck (confirmation); CERT r5.2 users 40% validation / 60% confirmation")
    p("independence limits: same IAM generator, same AIT release/attack family, same CERT benchmark family; AIT via verified subsets")
    ma = pd.read_csv(T / "table_model_adequacy.csv")
    for r in ma.itertuples():
        p(f"  {r.domain:4s} {r.objective:22s} {r.evidence_model:16s} cal={r.calibration_method:8s} AUROC {r.AUROC}  PRskill {r.PR_skill}  "
          f"BSS {r.BSS}  ECE {r.ECE}  slope {r.calibration_slope}  -> {r.adequacy_status} ({r.reason}); autonomous eligible: {r.adequacy_status == 'VALIDATED'}")
    mv = pd.read_csv(T / "main_comparison_validated_models.csv")
    p("AVOI vs baselines on VALIDATED models (confirmation, raw policies):")
    for r in mv[mv["domain"] == "Controlled IAM"].itertuples():
        p(f"  {r.method:26s} coverage {r.autonomous_coverage}  UAR {r.UAR}  loss {r.expected_loss}  acquisitions {r.mean_acquisitions}")
    p("  AIT-LDS v2.0 and CERT: no VALIDATED evidence model")
    st = pd.read_csv(T / "statistics.csv")
    p("strongest baseline (expected loss, validated IAM): All Evidence 0.398; Information Gain 0.423 (AVOI 0.440)")
    for comp in ("AVOI vs All Evidence", "AVOI vs Checklist", "AVOI vs Information Gain", "AVOI vs Generic VOI"):
        for m in ("mean_acquisitions", "UAR", "expected_loss"):
            r = st[(st["comparison"] == comp) & (st["metric"] == m)].iloc[0]
            p(f"  {comp:26s} {m:18s} diff {r.difference:+.4f} [{r.ci_low:+.4f}, {r.ci_high:+.4f}]  Holm p={r.p_holm:.3g}")
    rc = pd.read_csv(T / "risk_coverage_aurc.csv")
    rv = rc[(rc["adequacy_mode"] == "raw_validated_models_only") & rc["AURC_UAR_normalized"].notna()]
    p("risk-coverage AURC (validated IAM, raw): " + ", ".join(f"{r.method} {r.AURC_UAR_normalized:.4f}" for r in rv.itertuples()))
    ge = pd.read_csv(T / "adequacy_gate_effect.csv")
    p("adequacy-gate coverage cost:")
    for r in ge.itertuples():
        p(f"  {r.domain:36s} {r.scope:22s} {r.adequacy_status:22s} UAR {r.raw_AVOI_UAR} -> {r.gated_AVOI_UAR}; coverage {r.raw_coverage} -> {r.gated_coverage}")
    hy = pd.read_csv(T / "stage2_hypotheses.csv")
    for r in hy.itertuples():
        p(f"  {r.hypothesis} {'' if pd.isna(r.domain) else '[' + r.domain + ']'}: {r.verdict}")
    p("paths:")
    for x in ["results/stage2/tables/table_model_adequacy.md", "results/stage2/tables/main_comparison_validated_models.md",
              "results/stage2/tables/main_comparison_raw.md", "results/stage2/tables/main_comparison_enforced.md", "results/stage2/figures/",
              "results/final_report_v2/RESULTS.md", "results/final_report_v2/FAILURE_ANALYSIS.md", "results/final_report_v2/CLAIMS_ALLOWED.md",
              "results/final_report_v2/PAPER_RESULTS.tex"]:
        p(f"  {x}")
    for f in sorted((S2 / "figures").glob("*.pdf")):
        p(f"    {f.relative_to(ROOT).as_posix()} (+ .png)")
    p("=" * 100); p("CONCLUSIONS"); p("=" * 100)
    p("1. Stage 1 established: AVOI cut evidence acquisitions sharply on all three datasets, but did not beat information gain on "
      "unsafe assurance (H2 not supported), lost to all-evidence on IAM expected loss, H1 was not supported as registered, and AIT "
      "exposed poor cross-testbed model transfer.")
    p("2. Stage 2 newly established: with a frozen adequacy policy, only 4/9 evidence models (all IAM) are eligible; AIT and CERT "
      "models are inverted, unsupported or miscalibrated; on validated IAM models the acquisition-efficiency result replicates on new "
      "scenarios (S3), the gate blocks all autonomy where adequacy fails (S2) and every UAR reduction it causes costs coverage (S4); "
      "the prospective matched-safety construct was still degenerate.")
    p("3. AVOI can legitimately claim: substantially fewer acquisitions than exhaustive/fixed-order collection within adequacy-validated "
      "evidence models (via value-based stopping), lower unsafe assurance than symmetric generic VOI, an asymmetric-loss effect on "
      "unsafe assurance, and a governed abstention mechanism that withholds autonomy when model adequacy fails.")
    p("4. AVOI must not claim: lower UAR than information gain, lower loss than all-evidence, superiority over all strong baselines, "
      "efficiency at matched safety, generalisation to AIT-LDS/CERT, that the gate improves acquisition, pre-registration of the "
      "adequacy condition, regulatory compliance, or replacement of human assurance review.")


if __name__ == "__main__":
    main()
