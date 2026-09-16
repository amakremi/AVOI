# Failure analysis — AVOI, Stage 3 (adaptive evidence selection and external-domain validation)

This file keeps difficult and negative Stage-3 results in, as required by the protocol. It does not restate Stage 1/2
failures (`results/final_report_v2/FAILURE_ANALYSIS.md`), which are unaffected by Stage 3.

## 1. Objectives with a fixed (non-adaptive) ranking

None. All three WP1 objectives show a non-trivial rank-reversal rate at steps ≥ 2 (IAM-01: 0.564, IAM-02: 0.589,
IAM-03: 0.546) and a Holm-significant history-permutation test (p = 0.0003 each). There is no WP1 objective on which
AVOI's ranking is effectively frozen by the evidence model itself. Even IAM-01, where Adaptive and Frozen-Order AVOI
produce *byte-identical outcomes* at fixed horizons (Section 3 below), still re-ranks internally — the outcome
equivalence is a property of the terminal decision (order-independent given a fixed evidence set), not of a frozen
ranking.

## 2. No-rank-reversal histories

None found at the objective level (see §1). At the individual-episode-step level, 41-46% of observed steps do *not*
show a rank reversal (i.e., the adaptive next action matches what the frozen initial ranking would have picked) —
this is expected and not itself a failure: rank reversal is a strong test of adaptivity, and even a genuinely
history-dependent policy will often agree with its own initial ranking when the observed evidence is unsurprising.

## 3. Cases where Frozen-Order AVOI beats Adaptive AVOI

- **IAM-03-PRIV-AUTHZ, fixed horizon k=3**: Frozen-Order expected loss 0.398 vs Adaptive 0.520 (difference +0.121,
  95% CI [0.016, 0.242], sign-flip p = 0.025, Holm p = 0.098 — marginal after multiplicity correction across k∈{2,3}).
  At k=2 the same direction holds but is not significant (+0.020 [−0.043, +0.109]). This is the one WP1 objective
  whose evidence model is `RESTRICTED` for calibration failure (`MODEL_ADEQUACY_RESTRICTED`, calibration_slope 0.826,
  ECE 0.157). Re-ranking after each observation means AVOI is chasing a value signal computed from a poorly calibrated
  posterior; on this objective, committing to an initial (also imperfect, but fixed) ranking loses less than
  repeatedly re-optimizing against a noisy signal.
- **IAM-01-MFA-PRIV, both horizons**: a true tie (difference exactly 0.000, both CI bounds 0.000) rather than a
  Frozen-Order win, included here because it means adaptivity provided *no* measurable within-budget benefit on this
  objective — the k acquired items are the same set under both policies, so the terminal Bayes decision (a function of
  the evidence collected, not its order) cannot differ.
- **Normal operation, IAM-02-TERM-DISABLED** (Section 7 of RESULTS.md): under value-based stopping with
  validation-tuned thresholds (not the matched-horizon comparison), Frozen-Order AVOI achieves *better* coverage
  (0.902 vs 0.867) and lower loss (0.129 vs 0.156) than Adaptive AVOI, because it happens to keep collecting evidence
  for longer (1.902 vs 1.242 mean acquisitions) before the tuned stopping rule fires. This is a confound between
  selection order and total evidence collected, not a fixed-horizon result, and must not be read as contradicting the
  IAM-02 fixed-horizon win reported in §4.

## 4. Adaptive choices that increase loss relative to a matched-budget alternative

Beyond the pooled-level non-support of A2 (Section 6 of RESULTS.md), the only individually significant case where
adaptivity *increases* loss at a matched horizon is IAM-03-PRIV-AUTHZ at k=3 (§3 above). No other objective/horizon
combination shows a significant increase.

## 5. Failed / restricted external evidence models

- **AIT-EXFIL** (`RESTRICTED`, `INSUFFICIENT_ADEQUACY_SAMPLE_SUPPORT`): 0 violated episodes in the target testbed's
  (shaw) adequacy-validation split (504 episodes, 0 violated) — AUROC/PR-skill/calibration-slope are undefined (NaN)
  on that split by construction. This is not solely a sample-support technicality: leave-one-development-testbed-out
  worst-fold AUROC is only 0.638 (weak fold: russellmitchell, raw-feature AUROC 0.607), and the confirmation-testbed
  (wheeler+wilson) AUROC is a middling 0.729, driven down by wheeler at 0.563 (near chance). The chosen model's real
  transfer quality is mediocre, not merely under-sampled.
- **AIT-INTRUSION** (`RESTRICTED`, `INSUFFICIENT_ADEQUACY_SAMPLE_SUPPORT`): 6 violated episodes on shaw (2 independent
  groups), below the unchanged support threshold. Unlike AIT-EXFIL, this model's discrimination is genuinely strong
  and consistent: LODO worst-fold AUROC 0.837, shaw AUROC 0.994 [0.983, 1.000], confirmation-testbed AUROC 0.969
  (wheeler 0.966, wilson 0.977). This is the cleanest case of "adequate model, inadequate sample" in the project.
- Neither AIT claim was rescued by relaxing anything: the target-testbed role assignment (shaw) was frozen before any
  Stage-3 AIT label was read, and is not revisited post hoc even though a different, still-defensible pre-registered
  rule might have validated AIT-INTRUSION.

## 6. Zero-shot / target-adaptation / calibration failures

- **AIT-EXFIL calibration collapse**: because shaw's calibration split has zero violated episodes, the isotonic
  calibrator fit on it maps every confirmation-testbed evidence pattern to a posterior in [0.9956, 0.999999] — a
  15-decimal-digit-narrow band that makes the calibrated decision effectively constant. The target-calibrated variant's
  BSS on shaw's own validation split (1.000) is a calibration-metric artefact of that split having no positive class to
  be wrong about, not evidence of genuine improvement; on confirmation data the same calibrator destroys the
  (mediocre but non-trivial) ranking information the raw evidence carries. Every acquisition method, including All
  Evidence, gets identical loss (6.073) on AIT-EXFIL confirmation data as a direct consequence.
- **AIT-INTRUSION target adaptation is a no-op**: zero-shot and target-calibrated variants are numerically identical
  (same calibrator selected both ways) — target data did not change the outcome for this claim.
- **CERT-INSIDER target adaptation works as intended**: BSS improves 0.488 → 0.744 and ECE improves 0.113 → 0.017 with
  no change in discrimination — the one case in Stage 3 where target-partition calibration is unambiguously a net
  improvement rather than an artefact.
- **CERT-INSIDER's own residual failure**: at the adequacy-validation-tuned operating threshold, sensitivity to the
  violated (insider) class is exactly 0.0 (0 of 21 violated episodes correctly flagged), and MCC is 0.0. The adequacy
  policy's pass conditions (AUROC, BSS/ECE, sample support) do not test threshold-level minority-class recall, so a
  VALIDATED status coexists with an operating point that is currently useless for actually catching the insiders in
  the adequacy-validation split. This is reported, not hidden behind the VALIDATED label.

## 7. Unstable (direction-reversing) features

`table_feature_stability_stage3` flags, on development data only:
- **AIT-EXFIL**: `ait_query_monitoring` (violation-AUROC 0.616 on harrison but 0.346 on fox — a reversal exceeding the
  ±0.1-around-0.5 threshold in both directions).
- **AIT-INTRUSION**: `ait_query_web_access` (0.265 on russellmitchell vs 0.887 on harrison) and `ait_query_mail`
  (0.285 on russellmitchell vs 0.812 on wardbeck).
- **CERT**: no source is flagged (`direction_reverses` is False for all 10 CERT sources across r4.2/r5.2).

None of the flagged AIT sources were removed: the pre-committed rule required both a flag *and* a demonstrated
improvement in worst-development-fold AUROC after removal, decided before touching Stage-3 target/confirmation data,
and no removal trial met the bar for either claim. This is reported as a diagnostic finding rather than acted on
retroactively.

## 8. Gate false restrictions / coverage lost

- **IAM-03-PRIV-AUTHZ, enforced**: adequacy-enforced normal-operation coverage drops to 0.000 for every method
  (including AVOI, Frozen-Order AVOI, and all baselines) once the `RESTRICTED` gate is applied, from a raw coverage of
  1.000 — a 100-percentage-point coverage loss, consistent with the Stage-2 pattern that every gate-driven UAR
  reduction costs coverage (Stage-2 hypothesis S4). This is the expected, intended behaviour of an unchanged gate
  applied to an inadequate model, not a new failure mode.
- **AIT-EXFIL / AIT-INTRUSION, enforced**: both claims are RESTRICTED, so autonomous decisions are blocked entirely on
  confirmation data for every acquisition strategy; the diagnostic (non-enforced) rows in `table_external_avoi_stage3`
  exist only to characterise what the models *would* have done, per protocol Section 45, not to claim autonomous
  eligibility.

## 9. Non-significant adaptation results

- A1 is significant for all three objectives individually and pooled is not applicable (A1's rule is "at least one",
  already met) — no non-significant A1 result exists to report.
- A2's pooled test is not significant at either k (§Sections 4, 6 above) — this is the primary non-significant
  adaptation result of Stage 3 and is the reason A2 is reported as NOT SUPPORTED rather than partially supported.
- E2's efficiency comparisons against All Evidence and Information Gain are gated out by the pre-registered
  no-trivial-abstention rule before any significance test is even the deciding factor (the Wilcoxon tests themselves
  are all significant at p < 1e-75 given the large paired sample and consistent direction, but significance without
  the coverage-gate check would overstate the efficiency claim).
