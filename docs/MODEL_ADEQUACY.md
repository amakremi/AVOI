# Evidence-model adequacy (Stage-2 safety condition)

**Status in the research contribution.** The contribution remains AVOI (Assurance Value of Information). Model adequacy is
an applicability/safety condition motivated by Stage-1 observations (`docs/EXPERIMENTAL_HISTORY.md`); it is not a second
contribution, was not part of the Stage-1 pre-registration, and does not modify the AVOI formula
AVOI(a) = ΔR(a) − λC(a) − μP(a) − νD(a).

## Decision uncertainty vs model inadequacy
* *Decision uncertainty*: a trustworthy model, insufficient evidence in this episode → AVOI acquires evidence or escalates
  when remaining evidence has no positive value (stop reason `no_positive_value` / `exhausted` / `budget`).
* *Model inadequacy*: the evidence model itself lacks discrimination, calibration or sample support → autonomous AVOI is
  withheld for the whole model (stop reason `MODEL_ADEQUACY_RESTRICTED` / `MODEL_ADEQUACY_UNSUPPORTED`). More evidence is
  not assumed to repair this. Model inadequacy is never converted to NotAssured.

## Procedure (per domain × objective/micro-claim; `src/avoi/evaluation/stage2.py`)
1. **Development** (Stage-1 data): group-aware cross-fitting (IAM: 5 GroupKFold over scenario families; AIT: leave-one-
   testbed-out; CERT: 5 GroupKFold over users). Out-of-fold posteriors for full evidence + 3 random evidence subsets per
   episode. Model candidates TAN / Naive Bayes × α ∈ {0.5, 1, 2, 5} selected by out-of-fold log loss.
2. **Calibration** (development only): candidates none, Platt/sigmoid, isotonic, beta; selected by 5-fold group-CV log
   loss on the development out-of-fold posteriors; final calibrator fitted on all out-of-fold posteriors; final evidence
   model refitted on all development data. The calibrated posterior g(P(Y=1|E)) is used for every AVOI risk computation;
   predictive outcome probabilities P(O_a|E) are unchanged, post-outcome posteriors pass through g.
3. **Adequacy validation** (new data, disjoint from confirmation): full-evidence calibrated posteriors; AUROC, AUPRC,
   prevalence, PR skill = (AUPRC − prevalence)/(1 − prevalence), MCC, balanced accuracy, sensitivity (violated),
   specificity, Brier, BSS vs the development-prevalence predictor, log loss, ECE (10 bins), calibration slope and
   intercept; 5,000 group bootstrap resamples (IAM family, AIT testbed×hour block, CERT user).
4. **Decision** (`config/model_adequacy.yaml`, frozen): support (≥ 20 violated, ≥ 20 satisfied, ≥ 10 groups, ≥ 5 groups
   with a violation) → else RESTRICTED / INSUFFICIENT_ADEQUACY_SAMPLE_SUPPORT; discrimination (AUROC CI lower > 0.50 and
   PR-skill CI lower > 0) → else UNSUPPORTED; calibration (BSS > 0, ECE ≤ 0.10, 0.5 ≤ slope ≤ 1.5) → else RESTRICTED;
   otherwise VALIDATED. These are predefined Stage-2 autonomous-assurance eligibility criteria for this evaluation, not
   universal standards.
5. **Freeze**: decisions written with a hash to `results/stage2/ADEQUACY_DECISIONS.json`; the confirmation runner refuses
   to run if the Stage-2 protocol freeze or the decisions changed.
6. **Confirmation**: *raw* (ungated) acquisition-policy results and *enforced* results in which the same eligibility rule
   is applied to every method that depends on the evidence model (all compared methods do), so no method gains an
   advantage from abstaining.

Threshold tuning of all policies uses the adequacy-validation partition; confirmation labels only score decisions.
Sensitivity of the statuses to alternative thresholds is reported without changing the primary policy.
