# AVOI — Results, Stage 1 (original) and Stage 2 (adequacy safety condition and confirmation)

All numbers below are copied from generated tables. Stage-1 numbers come from `results/stage1_ungated/` (unchanged historical
artefacts). Stage-2 numbers come from `results/stage2/tables/`. Brackets are 95% intervals from a group bootstrap with
5,000 resamples, unless stated otherwise. Definitions used throughout:
- **UAR (unsafe assurance rate)** = #(Assured ∧ Y=0) / #(Y=0). HumanReview episodes with Y=0 stay in the denominator.
- **FAA (false assurance among assurances)** = #(Assured ∧ Y=0) / #(Assured).
- **Coverage** = the share of autonomous terminal decisions (Assured or NotAssured).
- **Loss matrix** (false assurance : false non-assurance : HumanReview) = 10 : 2 : 1.

**Two questions are kept separate throughout.** The *raw* (ungated) comparison measures acquisition-policy performance. The
*adequacy-enforced* comparison measures autonomous operation under evidence-model eligibility; the same rule is applied to
every method that depends on the evidence model. A lower UAR obtained by withholding autonomy is a **safety restriction
caused by adequacy gating, not an acquisition-policy improvement.**

## 1. Experimental history

- **Stage 1 (historical, unchanged).**
  - Protocol: pre-registered H1–H5, frozen configuration `4370311e…715c8`, git commit `7bb325c`.
  - Scale: 1,920 controlled-IAM episodes, 2,304 AIT-LDS v2.0 episodes, 969 CERT r4.2 episodes.
  - Stage 1 had **no evidence-model adequacy condition**.
  - Archive: `results/stage1_ungated/` (2,246 files, SHA-256 `MANIFEST.json`). Manuscript copies relabelled "AVOI" are in
    `results/stage1_ungated/manuscript/`.
- **Stage 2 (this revision).** Stage-1 AIT results revealed poor cross-testbed calibration, which motivated an
  evidence-model adequacy safety condition. The condition was **not part of the Stage-1 pre-registration**; it is
  prospective only relative to the Stage-2 freeze. The order of work was:
  1. Hypotheses S1–S4 and the adequacy policy (`config/model_adequacy.yaml`), partitions, grids and code were written
     and frozen in `results/stage2/EXPERIMENT_FREEZE_STAGE2.json` (combined SHA-256 `6a99f0fa…00e9`; git commit
     `5679e9e`).
  2. Adequacy was then validated on new data. The decisions were frozen in `results/stage2/ADEQUACY_DECISIONS.json`
     (SHA-256 `feec3a9d…368e`; commit `3ffaad3`).
  3. Only then was the confirmation partition evaluated (9 tasks, 0 failures).
- **Post-freeze changes.** All changes after the freeze were to presentation/analysis code, which is not hashed by the
  freeze (table and figure generation); raw outputs were not changed. Section 18 lists them.
- The AVOI decision formula AVOI(a) = ΔR(a) − λC(a) − μP(a) − νD(a) is unchanged from Stage 1; a test compares the file
  with commit `7bb325c`.

## 2. Stage-1 original findings

The Stage-1 findings are reproduced from the archive and have not been re-analysed. Held-out results at tuned operating
points:

| dataset | method | UAR | expected loss | mean acquisitions | coverage |
|---|---|---|---|---|---|
| IAM | AVOI | 0.009 [0.003, 0.018] | 0.381 [0.346, 0.419] | 1.638 | 0.761 |
| IAM | All Evidence | 0.008 [0.003, 0.015] | 0.316 [0.282, 0.354] | 6.167 | 0.842 |
| IAM | Information Gain | 0.009 [0.003, 0.018] | 0.353 [0.318, 0.392] | 2.268 | 0.793 |
| IAM | Generic VOI | 0.202 [0.175, 0.232] | 0.949 [0.840, 1.070] | 0.953 | 1.000 |
| AIT | AVOI | 0.305 [0.273, 0.336] | 1.477 [1.362, 1.590] | 0.566 | 0.872 |
| AIT | Information Gain | 0.305 [0.273, 0.336] | 1.476 [1.361, 1.589] | 1.261 | 0.873 |
| CERT r4.2 | AVOI | 0.031 [0.012, 0.052] | 0.441 [0.368, 0.523] | 1.346 | 0.931 |
| CERT r4.2 | Information Gain | 0.031 [0.012, 0.052] | 0.425 [0.352, 0.508] | 1.833 | 0.942 |

(Full table: `results/stage2/tables/stage1_recovered_results.csv`, labelled "Stage 1 (original, ungated)".)

Stage-1 pre-registered hypotheses (historical outcomes, not changed):
- **H1 — not supported** as originally registered. The matched-safety definition was degenerate: both methods selected
  operating points with zero acquisitions. The post-hoc correction (D1) remains exploratory.
- **H2 — not supported** on all three datasets: AVOI did not have lower UAR than information gain at matched budget.
- **H3** — supported on IAM and CERT; not supported on AIT.
- **H4** — supported on all three datasets.
- **H5** — supported as registered. Caveat: escalation mainly prevented false *non*-assurance and did not reduce false
  assurance relative to the no-escalation variant.

## 3. Motivation for the model-adequacy safety condition

- **What Stage 1 showed on AIT.** The evidence model fitted on one testbed transferred poorly to the other:
  full-evidence ECE ≈ 0.26, calibration slope ≈ 0.19, and false assurances issued at terminal belief ≥ 0.95. Every
  method had UAR ≈ 0.31.
- **Why that matters for AVOI.** AVOI values evidence through the model's P(Y|E) and P(O_a|E). If those probabilities
  are wrong, AVOI's value estimates and its stop decisions are also wrong, however the acquisition order is chosen.
- **What Stage 2 therefore asks.**
  1. Can an adequacy check made in advance on independent validation data identify such models?
  2. What happens when autonomous AVOI is withheld for them?
- **What the condition is not.** It does not change the AVOI formula. It adds no model-quality penalty. It never
  converts inadequacy into NotAssured: gated episodes return HumanReview with reason `MODEL_ADEQUACY_RESTRICTED` or
  `MODEL_ADEQUACY_UNSUPPORTED`.

## 4. Stage-2 data independence and confirmation design

Details are in `docs/STAGE2_DATA_INDEPENDENCE.md`. Stage-1 data serve only as **development** data (model fitting and
calibrator selection).

| domain | adequacy validation + threshold tuning | confirmation | independence |
|---|---|---|---|
| Controlled IAM | 128 new live scenarios (families 0–15), 768 episodes | 192 new scenarios (families 16–39), 1,152 episodes | new generator seed 20261103 (0 seed collisions); same generator and objectives |
| AIT-LDS v2.0 | testbed *fox* (720 windows × 2 micro-claims) | testbeds *harrison*, *wardbeck* (1,440 windows × 2) | testbeds unused in Stage 1; same release and attack family. Obtained as CRC-verified range-request subsets of the official archives |
| CERT | r5.2, 40% of 349 sampled users (140 users, 482 user-weeks) | r5.2, remaining 209 users (769 user-weeks) | different official release; same benchmark family; four label-blind release-harmonisation rules documented |

Threshold selection for every policy used the validation partition. Confirmation labels were used only to score frozen
decisions. **Limitation:** all three confirmation sources share generators or benchmark families with the development
data. Stage 2 therefore tests transfer to new scenarios, testbeds and releases, not to unrelated datasets.

## 5. Evidence-model adequacy

Source: `results/stage2/tables/table_model_adequacy.*`; figure `model_adequacy_diagnostics`. Metrics were computed on the
adequacy-validation partition with frozen development models.

**Primary policy (frozen).** A model is VALIDATED only if all of the following hold:
- Sample support: ≥ 20 violated cases, ≥ 20 satisfied cases, ≥ 10 groups, and ≥ 5 groups with a violation. Failing
  support gives RESTRICTED (`INSUFFICIENT_ADEQUACY_SAMPLE_SUPPORT`).
- Discrimination: AUROC CI lower bound > 0.50 and PR-skill CI lower bound > 0. Failing gives UNSUPPORTED.
- Calibration: BSS > 0, ECE ≤ 0.10, and slope in [0.5, 1.5]. Failing gives RESTRICTED.

| domain / model | selected model + calibrator | violated / groups | AUROC | PR skill | BSS | ECE | slope | status (reason) |
|---|---|---|---|---|---|---|---|---|
| IAM-01-MFA-PRIV | TAN α=0.5 + beta | 39 / 16 | 0.999 [0.997, 1.000] | 0.997 [0.990, 1.000] | 0.888 | 0.048 | **1.70** [1.31, 49.5] | RESTRICTED (calibration) |
| IAM-02-TERM-DISABLED | TAN α=2 + none | 41 / 16 | 0.998 [0.994, 1.000] | 0.994 [0.979, 1.000] | 0.937 | 0.024 | 1.32 | VALIDATED |
| IAM-03-PRIV-AUTHZ | TAN α=5 + none | 46 / 16 | 0.832 [0.787, 0.879] | 0.568 [0.482, 0.692] | 0.316 | 0.089 | 1.21 | VALIDATED |
| IAM-04-DORMANT | NB α=1 + none | 50 / 16 | 0.952 [0.922, 0.983] | 0.772 [0.634, 0.929] | 0.779 | 0.018 | 1.20 | VALIDATED |
| IAM-05-BREAKGLASS | TAN α=0.5 + beta | 57 / 16 | 0.993 [0.982, 0.999] | 0.983 [0.955, 0.998] | 0.850 | 0.055 | **4.65** [2.24, 126] | RESTRICTED (calibration) |
| IAM-06-ACCESS-REVIEW | NB α=1 + isotonic | 73 / 16 | 0.940 [0.893, 0.976] | 0.877 [0.791, 0.948] | 0.598 | 0.049 | 1.26 | VALIDATED |
| AIT-EXFIL | NB α=5 + sigmoid | 343 / 120 | **0.024** [0.013, 0.038] | −0.350 [−0.464, −0.257] | −0.451 | 0.587 | −6.55 | UNSUPPORTED (discrimination, calibration) |
| AIT-INTRUSION | TAN α=5 + sigmoid | **9** / 120 (3 groups with violation) | 0.686 [0.388, 0.807] | 0.021 [0.001, 0.084] | −0.002 | 0.003 | 0.63 | RESTRICTED (sample support; also fails discrimination and calibration) |
| CERT-INSIDER | TAN α=5 + none | 202 / 140 | 0.764 [0.678, 0.848] | 0.451 [0.312, 0.596] | 0.080 | **0.183** | **0.28** | RESTRICTED (calibration) |

**Eligibility.** 4 of 9 evidence models are eligible for autonomous AVOI, all of them IAM: IAM-02, IAM-03, IAM-04 and
IAM-06. No AIT or CERT model is eligible.

**How each model failed:**
- **AIT-EXFIL.** Its ranking is *inverted* on the new testbeds (AUROC 0.02): the evidence pattern associated with
  exfiltration in development points the other way on fox.
- **AIT-INTRUSION.** It has too few validation violations (9) for adequacy to be assessed.
- **CERT r5.2.** It discriminates moderately but is strongly over-confident (slope 0.28, ECE 0.18).
- **IAM-01 and IAM-05.** They discriminate almost perfectly but are *under*-confident (slope > 1.5). Their slope CIs are
  unbounded above because the classes are nearly separable. The frozen slope rule therefore restricts two models whose
  confirmation behaviour turned out to be reasonable (Sections 14 and 18).

**Calibration before/after** (`table_calibration_pre_post`). Development-selected calibrators changed validation ECE:
- AIT-EXFIL: 0.203 → 0.587. Sigmoid, selected on leave-one-testbed-out development predictions, did not transfer.
- IAM-06: 0.089 → 0.049.
- IAM-01: 0.061 → 0.048.

ROC/PR metrics assess the underlying evidence model, not the AVOI acquisition policy.

## 6. Stage-2 validated-domain AVOI results

Primary Stage-2 evaluation: confirmation episodes of **VALIDATED** models only (IAM-02/03/04/06; 768 episodes; raw
policies at validation-tuned thresholds). Source: `main_comparison_validated_models`.

| method | coverage | UAR | FAA | expected loss | bal. acc. | MCC | mean acq. | median acq. | norm. cost | privacy | HumanReview |
|---|---|---|---|---|---|---|---|---|---|---|---|
| All Evidence | 0.771 | 0.000 [0.000, 0.000] | 0.000 | **0.398** [0.362, 0.438] | 0.849 | 0.690 | 6.000 | 6 | 1.546 | 0.378 | 0.229 |
| Checklist | 0.733 | 0.010 [0.000, 0.023] | 0.010 | 0.452 [0.397, 0.513] | 0.832 | 0.653 | 4.612 | 4 | 1.135 | 0.307 | 0.267 |
| Random (20 seeds) | 0.723 | 0.004 [0.001, 0.007] | 0.004 | 0.414 [0.377, 0.450] | 0.845 | – | 4.294 | 3.7 | 1.222 | 0.343 | 0.277 |
| Cheapest First | 0.671 | 0.007 [0.000, 0.017] | 0.007 | 0.434 [0.387, 0.483] | 0.840 | 0.670 | 5.263 | 6 | 1.154 | 0.343 | 0.329 |
| Information Gain | 0.738 | 0.003 [0.000, 0.011] | 0.003 | 0.423 [0.382, 0.467] | 0.828 | 0.644 | 2.531 | 1 | 1.057 | 0.322 | 0.262 |
| Generic VOI | 1.000 | 0.268 [0.220, 0.321] | 0.152 | 1.138 [0.930, 1.393] | 0.812 | 0.636 | 0.960 | 1 | 0.553 | 0.200 | 0.000 |
| Confidence Threshold | 0.634 | 0.014 [0.003, 0.027] | 0.014 | 0.467 [0.414, 0.525] | 0.842 | 0.677 | 4.811 | 5 | 1.197 | 0.315 | 0.366 |
| Myopic Cost-Sensitive VOI | 1.000 | 0.007 [0.000, 0.017] | 0.007 | 0.578 [0.508, 0.656] | 0.769 | 0.524 | 1.150 | 1 | 0.811 | 0.260 | 0.000 |
| Lookahead-2 | 0.659 | 0.003 [0.000, 0.011] | 0.004 | 0.430 [0.393, 0.469] | 0.828 | 0.649 | 1.591 | 1 | 0.833 | 0.285 | 0.341 |
| **AVOI** | 0.677 | 0.003 [0.000, 0.011] | 0.004 | 0.440 [0.402, 0.480] | 0.828 | 0.647 | **1.454** | 1 | 0.962 | 0.283 | 0.323 |

AIT and CERT have no VALIDATED model, so no primary validated-domain comparison exists for them. Their raw
(diagnostic) results are in Section 14.

The table for all nine models, and the same comparison with the gate enforced for every method, are in
`main_comparison_raw` and `main_comparison_enforced`.

## 7. Acquisition efficiency

On VALIDATED IAM models (paired Wilcoxon signed-rank tests, Holm-adjusted within each metric; AVOI − comparator; 768
pairs), AVOI used fewer acquisitions than:

| comparator | acquisition difference |
|---|---|
| All Evidence | −4.55 [−4.57, −4.52] (Holm p = 1.7e-133) |
| Checklist | −3.16 [−3.25, −3.06] (Holm p = 2.3e-129) |
| Cheapest First | −3.81 |
| Confidence Threshold | −3.36 |
| Random | −2.84 |
| Information Gain | −1.08 [−1.21, −0.95] (Holm p = 3.9e-39) |
| Lookahead-2 | −0.14 [−0.19, −0.08] (Holm p = 2.2e-6) |

AVOI used **more** acquisitions than:
- Generic VOI: +0.49.
- Myopic Cost-Sensitive VOI: +0.30.

Both of those terminate autonomously on every episode, with higher UAR (Generic VOI) or higher loss (Myopic).

**Normalised acquisition cost.** AVOI was cheaper than All Evidence (−0.58), Checklist (−0.17), Information Gain
(−0.09), Cheapest First, Confidence Threshold and Random. It was **more expensive** than:
- Lookahead-2: +0.13 [0.11, 0.15], despite fewer acquisitions — AVOI chose costlier sources.
- Myopic VOI: +0.15.
- Generic VOI: +0.41.

**S3** (acquisition efficiency on validated models versus fixed and exhaustive strategies) is **supported** for IAM. It is
not testable for AIT and CERT.

**Action selection is not adaptive in order** (figure `action_frequency_heatmap`, P(A_t = a | N_acq ≥ t) with n_t).
Every objective offers 5–7 admissible actions, yet on IAM confirmation:
- On IAM-01, IAM-02 and IAM-04, AVOI selected the same single action in every episode.
- On IAM-03, IAM-05 and IAM-06, it followed one fixed sequence.

What adapts per episode is *when to stop*, not *which evidence to acquire next*. The efficiency gain therefore comes from
value-based stopping over a model-ranked source order; these panels are not evidence of adaptive source selection.

**Zero-acquisition analysis** (`zero_acquisition`).
- IAM AVOI: P(N_acq = 0) = 0; E[N_acq] = 1.48. Every VALIDATED-model episode was acquisition-required.
- AIT raw AVOI: P(N_acq = 0) = 0.50, from AIT-EXFIL, where the tuned policy escalates without acquiring. All
  threshold-stopping baselines acquire nothing on AIT (P(N_acq = 0) = 1).
- CERT: every method acquired evidence.

## 8. Safety and expected-loss comparison

On VALIDATED IAM models:

- **Versus Information Gain.** AVOI's UAR is identical (0.003 vs 0.003; exact McNemar p = 1). Its expected loss is
  numerically higher: +0.017 [−0.001, 0.035]; Wilcoxon Holm p = 0.35. Information gain remains a strong baseline and
  **wins on expected loss and coverage** (0.738 vs 0.677). AVOI wins on acquisitions, cost and privacy (−0.038).
- **Versus All Evidence.** AVOI has **higher expected loss**: +0.042 [0.005, 0.082]. The bootstrap CI excludes 0; the
  Wilcoxon Holm p is 0.21. UAR is +0.0035 [0.000, 0.011]. Exhaustive evidence gives better decisions at 4.1× the
  acquisitions and 1.6× the cost. All Evidence is a reference point, not a straw man.
- **Versus Generic (symmetric) VOI.** AVOI's UAR is lower: −0.265 [−0.315, −0.219] (exact McNemar Holm p = 2.4e-22).
  Its mean expected loss is lower: −0.70 [−0.93, −0.50]. The rank-based Wilcoxon on per-episode loss is not significant
  (p = 0.38, Holm = 1) because most per-episode differences are small (1 vs 0). Generic VOI's mean loss is driven by rare
  10-point false assurances. Part of the UAR gap comes from AVOI's HumanReview option (coverage 0.677 vs 1.000), which
  Generic VOI does not have.
- **Versus Checklist, Confidence Threshold, Cheapest First and Random.** No significant UAR or expected-loss difference
  after Holm correction.
- **Versus Lookahead-2.** Expected loss +0.010 [0.003, 0.021], not significant after Holm; UAR identical.
- **AVOI is not safer than all strong baselines.** Its UAR ties with the best baselines, and its expected loss is
  higher than All Evidence and not lower than Information Gain.

## 9. Asymmetric-loss ablation

Source: `asymmetric_loss_ablation`. AVOI with loss 10:2:1 is compared with an otherwise identical AVOI using symmetric
loss 2:2:1: same evidence model, actions, costs, privacy term and stopping framework. Differences are asymmetric −
symmetric.

| scope | UAR | FAA | expected loss | acquisitions | coverage | HumanReview | McNemar (unsafe only-asym / only-sym) |
|---|---|---|---|---|---|---|---|
| IAM, VALIDATED models | 0.003 vs 0.024: **−0.021 [−0.039, −0.004]** | −0.023 [−0.044, −0.005] | −0.112 [−0.180, −0.053] | +0.62 | +0.076 | −0.076 | 1 vs 7, p = 0.070 |
| IAM, all models (raw) | −0.011 [−0.020, −0.002] | −0.019 [−0.035, −0.006] | −0.169 [−0.213, −0.126] | +0.41 | +0.209 | −0.209 | 2 vs 7, p = 0.18 |
| AIT (raw diagnostic) | −0.0065 [−0.019, 0.000] | −0.004 | −0.012 [−0.048, 0.008] | +0.55 | −0.009 | +0.009 | 0 vs 6, p = 0.031 |
| CERT (raw diagnostic) | 0 vs 0 | n/a | 0 | +1.23 | 0 | 0 | – |

**Effect of the asymmetric loss:**
- Unsafe assurance and false assurance among assurances fall (bootstrap CIs exclude 0 on IAM).
- Expected loss falls.
- AVOI buys more evidence before deciding.
- On IAM it *increases* coverage: the symmetric variant escalates more often.

The paired McNemar tests on the few discordant unsafe assurances are not significant at 0.05 on IAM, so the size of the
UAR effect is uncertain. On CERT both variants escalated every episode at the tuned threshold.

## 10. Risk-coverage results

Figures: `risk_coverage_raw` (acquisition behaviour) and `risk_coverage_adequacy_enforced` (deployment view). Table:
`risk_coverage_aurc`. The UAR denominator is constant along every curve (verified for all curves and by a unit test).

**Normalised area under the UAR–coverage curve, raw, VALIDATED IAM models:**

| method | AURC |
|---|---|
| AVOI | 0.0023 |
| Lookahead-2 | 0.0023 |
| Information Gain | 0.0024 |
| Random | 0.0030 |
| Checklist | 0.0039 |
| Cheapest First | 0.0062 |
| Confidence Threshold | 0.0974 |

- AVOI's risk-coverage trade-off is far better than confidence-threshold stopping; its UAR reaches 0.5 near full
  coverage. It is essentially tied with Information Gain and Lookahead-2.
- These AURCs are descriptive; no inferential test was pre-specified.
- Pooled over all six IAM models (raw), AVOI's AURC is 0.0046, versus 0.0165 for Information Gain and 0.0901 for
  Confidence Threshold.

**Adequacy-enforced view:**
- AIT and CERT curves collapse to the single point (coverage 0, UAR 0). This is **complete abstention / withheld
  autonomy**, not safety performance.
- IAM coverage is capped at 0.667, because two of six models are gated.

**Behaviour near coverage = 1 (checked, not smoothed).** On CERT (raw), several curves drop from UAR ≈ 0.45 to 0 exactly
at coverage 1.0. On AIT, the confidence-threshold curve drops at coverage 1. The cause is the most permissive threshold,
at which no episode escalates:
- The autonomous argmin decision under the 10:2 loss is NotAssured unless P(Y=1|E) > 10/12.
- At that threshold the policies therefore issue almost only NotAssured decisions, so UAR is 0 while coverage is 1.

This is the same degeneracy that affects matched safety (Section 18). Here it is a correct consequence of the loss
matrix, not a counting error.

## 11. Evidence-budget results

Source: `budget`; figure `budget_performance_curve`.
- A hard budget k means *at most* k acquisitions; policies may stop earlier. Thresholds were not re-tuned per k.
- For k ≥ an objective's action count the budget cannot bind, so results are carried forward. This avoids a composition
  artefact in the pooled curves.

**VALIDATED IAM models, expected loss by k:**

| k | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| AVOI | 1.000 | 0.479 | **0.432** | 0.440 | 0.440 | 0.440 | 0.440 | 0.440 |
| Information Gain | 1.000 | 0.479 | 0.432 | 0.440 | 0.428 | 0.428 | 0.423 | 0.423 |
| Lookahead-2 | 1.000 | 0.535 | 0.500 | 0.435 | 0.435 | 0.432 | 0.430 | 0.430 |
| Checklist | 1.000 | 1.000 | 0.863 | 0.844 | 0.632 | 0.475 | 0.470 | 0.452 |
| All Evidence | 0.979 | 0.979 | 0.854 | 0.822 | 0.625 | 0.432 | 0.447 | 0.398 |

- **Small budgets.** AVOI and Information Gain reach low loss with 1–2 acquisitions; fixed-order strategies need 5 or
  more.
- **No gain from extra budget.** AVOI's loss does not improve beyond k = 3, because its value-based stopping leaves the
  extra budget unused.
- **Non-monotonicity (retained):**
  - AVOI rises slightly from k = 2 (0.432) to k = 3 (0.440).
  - All Evidence rises from k = 5 (0.432) to k = 6 (0.447).
  - Generic VOI on CERT rises from 2.27 at k = 2 to 3.08 at k = 3 (UAR 0.447 → 0.638).
  - These are consistent with additional, noisy evidence moving posteriors across a decision boundary. Individual
    episodes were not traced.

## 12. Missing-evidence robustness

Source: `missingness`; figures `missingness_robustness` and `missingness_uar_coverage`.
- Starting conditions: 20/40/60/80% of sources initially unacquired (100% = cold start). The remaining sources are
  revealed at the start under MCAR, source-block or adversarially inconvenient patterns.
- Thresholds were tuned at cold start.
- All quantities are reported jointly.

**Raw, IAM (all models):**

| condition | AVOI UAR | AVOI coverage | AVOI acquisitions |
|---|---|---|---|
| cold start | 0.013 | 0.785 | 1.48 |
| MCAR 20% | 0.013 | 0.797 | 0.19 |
| MCAR 80% | 0.031 | 0.788 | 1.09 |
| adversarial 80% | 0.020 | 0.781 | 1.35 |

- All Evidence stays at UAR 0.013 and coverage 0.842 in every condition, because it always ends with every source.
- Information Gain behaves similarly to AVOI: MCAR 80% gives UAR 0.018; adversarial 80% gives 0.038.
- Coverage is stable, so **the UAR changes are not abstention effects**. A partially pre-revealed evidence state can
  lead AVOI to stop earlier with more unsafe assurances than at cold start (UAR up to 0.031 vs 0.013).
- **Adequacy-enforced, IAM:** AVOI coverage is 0.45–0.49 in every mode and at every level, with UAR ≤ 0.009.
- **AIT and CERT (raw diagnostic).** These are dominated by model inadequacy:
  - CERT AVOI with partial evidence issues autonomous decisions with UAR 0.29–0.36 and expected loss 1.86–2.14.
  - At cold start, CERT AVOI escalates everything.

**Verdict:** AVOI remains *usable* under missing evidence for VALIDATED IAM models, but its unsafe-assurance rate is not
invariant to the missingness pattern.

## 13. Privacy trade-off

Source: `privacy`; figure `privacy_safety_tradeoff`. The privacy weight μ is shown at its actual values, with thresholds
re-tuned on validation for each μ. **The privacy metric is an experimental exposure proxy (count of distinct privacy
categories touched / 10), not a universal legal or privacy-risk value.**

| IAM, μ | 0 | 0.02 (primary) | 0.10 | 0.25 | 0.50 | 1.00 |
|---|---|---|---|---|---|---|
| privacy exposure | 0.282 | 0.282 | 0.282 | 0.282 | 0.182 | 0.113 |
| expected loss | 0.394 | 0.394 | 0.389 | 0.389 | 0.523 | 0.694 |
| UAR | 0.013 | 0.013 | 0.013 | 0.013 | 0.011 | 0.000 |
| coverage | 0.785 | 0.785 | 0.762 | 0.762 | 0.582 | 0.503 |
| acquisitions | 1.51 | 1.48 | 1.36 | 1.36 | 1.07 | 0.50 |

- **IAM.** Weighting privacy reduces exposure only once μ ≥ 0.5, and it costs decision quality: loss rises by 0.13–0.30
  and coverage falls by 0.20–0.28. The UAR reduction at μ = 1 comes with the coverage drop.
- **CERT.** Exposure falls from 0.44 (μ = 0) to 0.08 (μ ≥ 0.5), but every setting escalates almost every episode.
- **AIT.** Exposure is already below 0.005.

## 14. Model-adequacy boundary experiments

Source: `table_boundary`, `adequacy_gate_effect`, `model_vs_decision_uncertainty.md`.

| model | status | raw AVOI UAR | gated UAR | raw coverage | gated coverage | raw expected loss | gated expected loss |
|---|---|---|---|---|---|---|---|
| IAM-01-MFA-PRIV | RESTRICTED | 0.017 [0.000, 0.061] | 0 | 1.000 | 0 | 0.292 | 1.000 |
| IAM-05-BREAKGLASS | RESTRICTED | 0.038 [0.010, 0.071] | 0 | 1.000 | 0 | 0.312 | 1.000 |
| AIT-EXFIL | UNSUPPORTED | 0 | 0 | **0.000** | 0 | 1.000 | 1.000 |
| AIT-INTRUSION | RESTRICTED | 0.600 [0.167, 1.000] (few Y=0) | 0 | 0.983 | 0 | 0.080 | 1.000 |
| CERT-INSIDER | RESTRICTED | 0 | 0 | **0.000** | 0 | 1.000 | 1.000 |
| IAM, domain (4 V + 2 R) | – | 0.013 [0.004, 0.024] | 0.002 [0.000, 0.007] | 0.785 | 0.451 | 0.394 | 0.627 |

**Interpretation, per model:**

- **AIT-EXFIL and CERT.** At the validation-tuned threshold, the *raw* AVOI policy already escalated every
  confirmation episode. The inadequate model made no risk level acceptable on validation data. The gate therefore
  changed nothing, and no unsafe assurance was avoided *by the gate*.
  - Evidence that the inadequacy is a model-level property: the All Evidence policy, which acquires every source and
    decides autonomously, has realised-minus-predicted loss **+2.28** on CERT (autonomous error rate 0.315) and **+0.97**
    on AIT-EXFIL (error rate 0.71). Acquiring more evidence does not repair a miscalibrated or inverted model.
- **AIT-INTRUSION.** Raw AVOI decided 98% of episodes autonomously with low loss (0.080). But 9 of the 15 confirmation
  violations were assured (UAR 0.60 [0.17, 1.00]). The gate removes those false assurances at the cost of 98% of
  coverage.
- **IAM-01 and IAM-05** (restricted for under-confidence only):
  - Raw AVOI was fully autonomous, with UAR 0.017 (IAM-01) and 0.038 (IAM-05) and expected loss 0.29 and 0.31.
  - Realised loss was close to the model's predicted loss: gaps of +0.11 and +0.02 for AVOI, and +0.05 and +0.01 for
    All Evidence.
  - Gating prevented 1 and 4 false assurances, but withheld 168 and 178 correct autonomous decisions, and raised
    expected loss to 1.0.
  - These are cases where **the frozen policy restricted useful autonomy**.
- **Domain-level IAM.** Enforcement lowered UAR from 0.013 to 0.002 by lowering coverage from 0.785 to 0.451. This is a
  safety restriction, not an acquisition improvement.

**S1 (adequacy diagnosis): supported by the frozen rule, with a caveat.**
- Confirmation expected loss of raw AVOI was higher for non-validated than for validated models: 0.605 vs 0.440;
  difference CI [0.113, 0.220].
- The UAR difference was not significant: 0.0097 vs 0.0035; CI [−0.004, 0.017].
- **Caveat:** much of the loss difference comes from raw AVOI escalating all AIT-EXFIL and CERT episodes (loss 1 each),
  not from unsafe assurances.

**S2 (gate enforcement): supported.**
- 0 autonomous decisions for all five non-validated models.
- Every gated episode carries `MODEL_ADEQUACY_RESTRICTED` or `MODEL_ADEQUACY_UNSUPPORTED`; none was converted to
  NotAssured.
- VALIDATED models are unchanged.

**S4 (safety vs coverage): supported.**
- Every non-zero change in UAR co-occurred with a coverage loss: IAM-01 −0.017 / −1.00; IAM-05 −0.038 / −1.00;
  AIT-INTRUSION −0.600 / −0.98.
- AIT-EXFIL and CERT had ΔUAR = 0 and Δcoverage = 0.

## 15. Escalation analysis

Source: `escalation`. The table separates the two escalation types. Counts are on confirmation episodes for AVOI.

**A. Evidence-uncertainty escalation (raw AVOI, VALIDATED IAM models):**

| model | escalations | Y=1 | Y=0 | false non-assurances prevented | false assurances prevented | coverage lost |
|---|---|---|---|---|---|---|
| IAM-02 | 36 | 33 | 3 | 33 | 0 | 0.19 |
| IAM-03 | 111 | 70 | 41 | 70 | 0 | 0.58 |
| IAM-06 | 101 | 55 | 46 | 55 | 0 | 0.53 |
| IAM-04 | 0 | – | – | – | – | 0 |

- On VALIDATED IAM models, escalation prevented **false non-assurances only, never false assurances**. This replicates
  the Stage-1 H5 caveat.
- On the RESTRICTED models:
  - AIT-INTRUSION: 6 of 25 escalations prevented a false assurance.
  - CERT: 769 escalations; 157 false assurances and 106 false non-assurances prevented, and 506 correct autonomous
    decisions withheld.

**B. Model-adequacy escalation (gate):**

| model | gated episodes | decisions changed | false assurances prevented | false non-assurances prevented | correct decisions withheld |
|---|---|---|---|---|---|
| IAM-01 | 192 | 192 | 1 | 23 | 168 |
| IAM-05 | 192 | 192 | 4 | 10 | 178 |
| AIT-INTRUSION | 1,440 | 1,415 | 9 | 0 | 1,406 |
| AIT-EXFIL | 1,440 | 0 | 0 | 0 | 0 |
| CERT | 769 | 0 | 0 | 0 | 0 |

In AIT-EXFIL and CERT, the raw policy had already escalated every episode. Across all gated models, the gate prevented
14 false assurances and withheld 1,752 correct autonomous decisions.

## 16. Statistical results

Source: `statistics`. Tests on paired confirmation episodes of VALIDATED IAM models, AVOI versus each comparator:
- Wilcoxon signed-rank tests for acquisitions, cost, expected loss and privacy, with rank-biserial effect sizes.
- Exact McNemar tests on unsafe assurance among Y=0 episodes (sign-flip permutation test against Random).
- Holm correction within each metric; group bootstrap CIs of the difference (resampled by scenario family).

**Significant after Holm correction:**
- Fewer acquisitions than All Evidence, Checklist, Cheapest First, Confidence Threshold, Random, Information Gain and
  Lookahead-2. More acquisitions than Generic VOI and Myopic VOI.
- Lower cost than All Evidence, Checklist, Random, Cheapest First, Information Gain and Confidence Threshold. Higher cost
  than Generic VOI, Myopic VOI and Lookahead-2.
- Lower privacy exposure than every comparator except Generic VOI and Myopic VOI (both higher for AVOI); versus
  Lookahead-2 the difference is −0.0014.
- Lower UAR than Generic VOI (Holm p = 2.4e-22).
- Lower expected loss than Myopic VOI: −0.138 (Holm p = 2.3e-6).

**Not significant after Holm correction:**
- Every other UAR comparison.
- Expected loss versus All Evidence (bootstrap CI excludes 0, Holm-adjusted Wilcoxon p = 0.21), Information Gain,
  Checklist, Lookahead-2 and Random.

Following the protocol, no significance test compares a fully gated (abstaining) method with an autonomous method.
Adequacy-boundary models are analysed descriptively (Sections 14–15).

**LLM-only planner (secondary).** Setup: gemma4:e4b, temperature 0, thinking disabled; IAM confirmation families 16–23,
384 episodes, 0 invalid responses. Source: `llm_planner`. Raw results:

| method | UAR | expected loss | acquisitions | coverage |
|---|---|---|---|---|
| LLM planner (Bayes decision layer) | 0.007 | 0.357 | 5.10 | 0.841 |
| AVOI (value-stop, Bayes decision) | 0.000 | 0.372 | 1.65 | 0.836 |
| AVOI (tuned threshold) | 0.000 | 0.375 | 1.45 | 0.771 |

- The LLM planner reaches similar loss but acquires about 3× more evidence than AVOI.
- With the gate enforced, all three methods are restricted identically on IAM-01 and IAM-05.

## 17. Sensitivity

**Adequacy-policy sensitivity** (`adequacy_sensitivity`; figure `adequacy_sensitivity`). The primary policy is unchanged;
the alternatives are reported, not selected.

| variant | effect on eligibility |
|---|---|
| AUROC CI lower bound > 0.55 or > 0.60 | no change |
| minimum violated cases 10 or 40 | no change |
| ECE ≤ 0.15 | no change |
| ECE ≤ 0.05 | removes IAM-03 → 3 validated; enforced coverage (all domains) 0.108 → 0.091 |
| slope in [0.75, 1.25] | 2 validated; coverage 0.057 |
| slope in [0.25, 1.75] | admits IAM-01 → 5 validated; coverage 0.148; enforced UAR 0.0006 → 0.0012 |

AIT and CERT fail under **every** variant. IAM eligibility depends mainly on the calibration-slope interval.

**False-assurance penalty sensitivity** (`fa_sensitivity`). Expected loss is on each penalty's own scale.
- **IAM AVOI.** Raising the penalty from 2 → 5 → 10 → 20 lowers UAR (0.262 → 0.062 → 0.013 → 0.004) and coverage
  (0.93 → 0.79 → 0.78 → 0.65).
- **CERT AVOI.** It decides autonomously at penalties 2 and 5 (UAR 0.45) and escalates everything at 10 and 20.
- **Generic VOI** is insensitive to the penalty by construction (UAR 0.23 on IAM, 0.54 on CERT at every penalty).

## 18. Failure analysis summary

Full analysis: `FAILURE_ANALYSIS.md`.

**Model and data failures:**
1. AIT evidence models do not transfer across testbeds. EXFIL is inverted (Stage 1 and Stage 2); INTRUSION has only 9
   validation violations.
2. CERT r5.2 is over-confident: a model trained on r4.2 does not calibrate on r5.2.
3. The frozen calibration-slope rule restricts two near-perfectly discriminating IAM models whose confirmation behaviour
   was reasonable. The slope is unstable under near-separation.
4. The development-selected isotonic calibrator on IAM-06 produces extreme (0/1) posteriors. AVOI's predicted loss was
   0.000, while its realised loss was 0.110.

**Comparisons AVOI did not win:**
5. Information Gain ties AVOI on UAR and has numerically lower expected loss and higher coverage. All Evidence has
   significantly lower expected loss.
6. AVOI is more expensive than Lookahead-2, despite fewer acquisitions.

**Stage-2 evaluation-design failures:**
7. **The frozen non-degenerate matched-safety definition (UAR ≤ η AND coverage ≥ γ) is still degenerate.** On the
   VALIDATED IAM models, every validation-achieved operating point for AVOI, Information Gain, Checklist, Cheapest First,
   Lookahead-2 and Random (48 of 48 each) had **zero correct assurances**: always-NotAssured with no evidence counts as
   full coverage with UAR 0. The matched-safety comparison is therefore uninformative for efficiency (C14 not
   supported). The definition was not changed after the freeze. A future definition must also constrain false
   non-assurance or assurance recall.
8. Coverage-matched targets were rarely achieved by AVOI: 3 of 16 validated-model targets on validation. Its
   risk-threshold grid jumps across coverage levels, and achieved coverage often shifted on confirmation.

**Behavioural observations:**
9. Escalation on VALIDATED IAM models prevented only false non-assurances.
10. Budget and missingness non-monotonicities are retained (Sections 11–12).

**Presentation changes after the freeze.** None of these touched raw outputs or frozen code:
- Matched tables are now reported per evidence model instead of pooled across objectives, which differed by method.
- Budget curves carry k ≥ m forward.
- Scopes restricted to VALIDATED models were added for the ablation, budget and AURC tables.
- Slope-panel CIs are clipped for display.

## 19. Threats to validity

- **Construct.**
  - UAR, coverage and loss depend on the 10:2:1 loss matrix. The matched-safety construct is degenerate (Section 18).
  - Privacy exposure is a proxy.
  - Labels are objective predicates in IAM and attack-activity labels in AIT/CERT; **they are not compliance labels**.
- **Internal.**
  - Thresholds and calibrators were selected without confirmation labels, and adequacy decisions were frozen and hashed
    before confirmation.
  - The adequacy policy itself was designed after seeing Stage-1 AIT failures. It is therefore not independent of
    Stage-1 knowledge, although its thresholds were fixed before any Stage-2 label was used.
  - Analysis code is not hashed by the freeze.
- **External.**
  - Confirmation data share generators or benchmark families with development data: same IAM generator, same AIT
    release, same CERT family.
  - AIT uses verified subsets, not full archives.
  - BOTS v3 and LANL remain unusable (access gates not bypassed).
  - Only 4 of 9 models are eligible, all synthetic IAM; conclusions about autonomous AVOI rest on the controlled testbed.
- **Statistical.**
  - Only 16 IAM validation families; slope CIs unbounded; only 9 validation and 15 confirmation violations for
    AIT-INTRUSION.
  - Several comparisons are close to ties, and many tests were run (Holm within metric only).
- **LLM baseline.** It covers one local model (gemma4:e4b) on a subset; results are not general statements about LLM
  planners.

## 20. Supported claims

Classification details: `CLAIMS_ALLOWED.md`.

**Supported (bounded to VALIDATED IAM evidence models in Stage 2 unless noted):**
- AVOI substantially reduces evidence acquisitions relative to exhaustive and fixed-order strategies. This holds in
  Stage 1 (three datasets) and in Stage 2 on new IAM scenarios.
- Relative to symmetric Generic VOI, AVOI has lower unsafe assurance. Relative to identical symmetric-loss AVOI, the
  asymmetric loss lowers UAR and FAA (bootstrap CIs exclude 0; paired McNemar not significant).
- Evidence-model adequacy enforcement prevents autonomous AVOI decisions in domains that fail the predefined policy (S2),
  and its safety effect is always accompanied by coverage loss (S4).

**Partially supported:**
- Cost reduction: not versus Lookahead-2, Myopic or Generic VOI.
- Better risk-coverage trade-off than confidence thresholds: large but descriptive, one domain.
- Robustness under missing evidence.
- Privacy reduction when weighted: only at a loss and coverage cost.
- Adequacy as a condition for trustworthy value estimates: clear failures on AIT and CERT, but two restricted IAM models
  behaved acceptably.

**Not supported:**
- AVOI has lower UAR than Information Gain (H2 remains not supported; the gate does not change this).
- AVOI has lower expected loss than All Evidence.
- AVOI is safer than all strong baselines.
- AVOI generalises across all datasets: no AIT or CERT model is eligible.
- AVOI is more efficient at matched non-degenerate safety/coverage: the frozen construct is degenerate.
- AVOI should replace human assurance review.

Stage-1 H1 remains *not supported as registered* and H2 remains *not supported*; Stage 2 does not rescue either.

## Appendix — Final scientific interpretation

**A. Acquisition contribution.**
- **Does AVOI reduce the evidence burden?** Yes, relative to exhaustive collection (−4.55 acquisitions per episode),
  fixed checklist (−3.16), cheapest-first, confidence threshold, random order, information gain (−1.08) and lookahead-2
  (−0.14). This holds on VALIDATED IAM models in Stage 2 and on all three datasets in Stage 1.
- **What does it cost?** Versus all-evidence, +0.042 expected loss. Versus information gain, +0.017 loss (not
  significant) and 0.06 lower coverage. UAR ties with the best baselines.
- **Where does the gain come from?** On IAM it comes from value-based stopping, not from adaptive source ordering.

**B. Assurance-specific contribution.**
- Yes, the asymmetric loss changes unsafe-assurance behaviour. Versus identical symmetric-loss AVOI: UAR −0.021, FAA
  −0.023, expected loss −0.112, more acquisitions, higher coverage.
- Versus symmetric generic VOI, UAR is lower by 0.265.
- The paired McNemar test on the few discordant unsafe assurances is not significant, so the size of the effect is
  uncertain.

**C. Model adequacy.** Only four IAM evidence models satisfy the predefined eligibility policy: IAM-02, IAM-03, IAM-04
and IAM-06. No AIT-LDS or CERT model does, under any sensitivity variant.

**D. Safety condition.** When AVOI is withheld in inadequate domains:
- It issues no autonomous decisions there.
- The gate prevented 14 false assurances in total, across IAM-01, IAM-05 and AIT-INTRUSION.
- It removed all coverage for those models: 1,752 correct autonomous decisions withheld.
- IAM domain coverage fell from 0.785 to 0.451.
- For AIT-EXFIL and CERT, the ungated policy had already escalated everything, so the gate avoided no additional unsafe
  assurance.

**E. Generalisation.**

| on new data, the finding… | findings |
|---|---|
| replicated | acquisition efficiency on new IAM scenarios; asymmetric-loss safety effect versus symmetric variants; information gain and all-evidence remaining strong; escalation mainly preventing false non-assurance |
| did not replicate or generalise | any autonomous use on new AIT testbeds (discrimination inverted) or CERT r5.2 (miscalibrated); the Stage-1 CERT operating point (Stage 1 UAR 0.031 at coverage 0.93; Stage 2 escalates everything) |

**F. Where AVOI should not currently be used autonomously.**
- With the AIT-LDS exfiltration and intrusion models and the CERT insider model developed here.
- Whenever the evidence model has not passed an independent adequacy check.
- As a replacement for human assurance review.
- For efficiency claims at matched safety, until a non-degenerate construct is defined.
