# Stage 3 — external evidence models (AIT-LDS v2.0, CERT)

## 1. Class semantics (verified before any Stage-3 model training)

| Item | Definition (all domains) | Code |
|---|---|---|
| Y = 1 | assurance claim **holds** (AIT: no labelled activity of the micro-claim's type in the 10-minute window; CERT: no answer-key insider activity in the user-week) | `ait_episodes.build`, `cert.build` |
| Y = 0 | claim **refuted** (violation) | same |
| Assurance posterior | P(Y = 1 \| E) returned by every evidence model (`posterior`) | `models/tan.py`, `models/discriminative.py` |
| Violation class for ROC/PR | positive class = Y = 0 | `adequacy.point_metrics`: `viol = (y == 0)` |
| Score for AUROC / AUPRC | 1 − P(Y = 1 \| E) = P(violation \| E) | `roc_auc_score(viol, 1 - p)`, `average_precision_score(viol, 1 - p)` |
| PR skill | (AUPRC − prevalence_violated) / (1 − prevalence_violated) | same |

Tests: `tests/test_stage3.py::test_ait_class_orientation`, `::test_cert_class_orientation`.

## 2. Stage-2 AIT-EXFIL AUROC 0.024 — diagnosis (historical results unchanged)

Question: genuine inversion under transfer, or class-score orientation error?

Finding: **neither a metric orientation error nor an inversion of the uncalibrated model on new testbeds; it was a
non-monotone calibration map learned from inverted development cross-testbed predictions.** Evidence (development data
only — all five testbeds are Stage-3 development data):

1. The metric orientation is correct (Section 1).
2. The raw DNS statistic separates EXFIL windows perfectly within **every** testbed and in the same direction
   (violation-AUROC of the raw count = 1.00 on russellmitchell, santos, fox, harrison and wardbeck; violated windows have
   DNS counts 64–118, satisfied windows 0 (median)).
3. Stage-2 development used leave-one-testbed-out predictions over only two testbeds with pooled 50th/90th-percentile
   discretisation thresholds. Those out-of-fold posteriors were **inverted** (development OOF AUROC 0.249, calibration
   slope −0.42), because the absolute scale of the DNS counts differs between testbeds and a secondary source
   (monitoring) reverses its association (violation-AUROC 0.72 on russellmitchell, 0.26 on fox).
4. The development-selected Platt calibrator was fitted on those inverted predictions and learned a **negative slope**
   (b = −0.46). Applied to the final model — whose uncalibrated validation AUROC on fox was **0.976** — it inverted the
   ranking, giving AUROC 0.024.

Consequences for Stage 3 (development-only, frozen before validation):
* calibration maps that are decreasing in P(Y = 1 | E) are **semantically invalid** and excluded from calibrator selection
  (the adequacy gate itself is unchanged);
* AIT development uses all five historical testbeds with leave-one-testbed-out validation;
* candidate selection ranks by worst-development-testbed AUROC (robustness), requires positive median PR skill, and
  tie-breaks on log loss / Brier / ECE;
* a feature-stability analysis flags sources whose violation association reverses across development testbeds.

Stage-2 AIT-INTRUSION: violation prevalence is 0.7–1.4% of 10-minute windows per testbed (≈ 5–10 windows); any single
new testbed partition is expected to fail the unchanged sample-support rule mechanically.

## 2a. Candidate model scope

Development candidates evaluated: TAN and Naive Bayes (`src/avoi/models/tan.py`, reused unchanged) at α ∈
{0.5, 1, 2, 5}, and a HistGradientBoostingClassifier (`stage3_wp2.HGBEvidenceModel`, new — the only new model class,
not a large neural model). `avoi.models.discriminative.CalibratedLogisticModel` (Stage-1/2 regularized-logistic
evidence model) is available and interface-compatible but was **not** included in the Stage-3 candidate pool, since
TAN/NB/HGB already span the linear-vs-tree-ensemble range and no candidate-selection result in this run was close
enough (worst-fold AUROC within 0.01) for a fourth candidate class to plausibly change the selected model. This is a
scope limitation, noted for completeness rather than silently omitted.

## 2b. CERT new-release pool reduced from 4 to 2 releases (time-budget decision, made before any label was read)

The original design pooled four untouched CERT releases (r4.1, r5.1, r6.1, r6.2; public answer-key insider counts
3/4/5/5). All four archives were fully downloaded and MD5-verified (§ Stage-2/3 dataset manifest). Extraction uses a
single-threaded `bzip2` (no parallel-bzip2 tool was available in this environment); r4.1 (5GB compressed) took ~17 min
and r5.1 (11GB compressed) took **~110 min**. At that measured rate, r6.1 (20GB) and r6.2 (24GB) would together need a
further **~7-8 hours** of pure decompression before any processing could start.

**Decision (frozen in `config/stage3.yaml` before r4.1/r5.1 labels, answer keys, or any evidence-model result was
inspected):** the CERT new-release pool is reduced to **r4.1 + r5.1** (7 insiders combined). r6.1.tar.bz2 and
r6.2.tar.bz2 remain on disk, fully downloaded and MD5-verified, for future continuation; they were not extracted or
processed further. This is a practical scope reduction driven by wall-clock decompression time, decided before seeing
any consequence for the adequacy outcome - it is reported here for transparency, not concealed by silently redefining
"new releases" as r4.1+r5.1 without comment.

**Consequence for sample support.** With only 7 insiders pooled (versus 17 in the original 4-release design), the
CERT adequacy-validation partition may not reach the required 5 independent groups with a violation even if the
model discriminates well - this is reported as the actual outcome, not adjusted for.

## 3. Untouched external data (verified against official sources on 2026-09-15)

* AIT-LDS v2.0 (Zenodo record 5789064) has eight testbeds. Used before Stage 3: russellmitchell, santos (Stage 1); fox,
  harrison, wardbeck (Stage 2). **Untouched: shaw (17.6 GB), wheeler (19.6 GB), wilson (26.5 GB).**
  Role rule (fixed before any Stage-3 label is read, same size rule as Stage 2): smallest (shaw) → testbed A
  (target calibration 40% / adequacy validation 60%, label-blind split by hour block); wheeler and wilson → confirmation.
* CERT (figshare article 12841247): releases used before Stage 3: r4.2 (Stage 1), r5.2 (Stage 2). Untouched releases with
  the logon/device/file/http/email/LDAP/psychometric schema family: r4.1, r5.1, r6.1, r6.2 (r1–r3.x have a different
  schema and are excluded). The public answer-key index `insiders.csv` lists 3, 4, 5 and 5 insider users for these
  releases (17 in total) — a single release cannot meet the unchanged support rule (≥ 5 groups with a violation in the
  validation partition). Design fixed before downloading: **pool r4.1 + r5.1 + r6.1 + r6.2** (later reduced to r4.1+r5.1
  for the time-budget reason in Section 2b), reuse the Stage-1 episode sampling rule per release, and split users
  label-blind by hash of `release:user` into calibration 20% / adequacy validation 40% / confirmation 40%. The
  larger-than-recommended validation share is a pre-specified response to the public insider count, not to observed
  class counts.

## 3a. Stage-3 outcome on the pre-committed target testbed (honest, not worked around)

The role rule (Section 3, fixed before any Stage-3 label was read: smallest untouched archive by size → target A) chose
**shaw**. After building shaw's episodes, its label prevalence turned out to be:

| testbed | role | AIT-EXFIL violated | AIT-INTRUSION violated |
|---|---|---|---|
| shaw | target A (calibration + adequacy validation) | **0.12%** (1/864) | 0.69% (6/864) |
| wheeler | confirmation | 64.6% (465/720) | 0.56% (4/720) |
| wilson | confirmation | 57.5% (497/864) | 0.69% (6/864) |

Shaw genuinely contains almost no labelled DNS-exfiltration activity — AIT-LDS v2.0 testbeds do not all carry the same
mix of injected attacks. On shaw's adequacy-validation split (504 episodes after the 40/60 calibration split), AIT-EXFIL
has **0 violated episodes** and AIT-INTRUSION has 6 (2 groups with a violation). Both claims are therefore **RESTRICTED**
(`INSUFFICIENT_ADEQUACY_SAMPLE_SUPPORT`) under the unchanged policy.

**Corrected note (verified by direct computation, superseding an earlier imprecise draft of this section that
conflated median development PR-skill with AUROC):** the two claims are *not* equally well-supported by discrimination.
AIT-INTRUSION (chosen: TAN, α = 2.0) has robust cross-testbed discrimination — leave-one-development-testbed-out worst-fold
AUROC 0.837, shaw target-calibrated AUROC 0.994 [0.983, 1.000], and pooled confirmation-testbed (wheeler+wilson)
AUROC 0.969 (wheeler 0.966, wilson 0.977) — computed directly from the target-calibrated posterior against the
confirmation labels. It is RESTRICTED purely on sample support (6 violated episodes / 2 independent groups on shaw). AIT-EXFIL
(chosen: HistGradientBoostingClassifier) is materially weaker: leave-one-development-testbed-out **worst-fold AUROC is
only 0.638** (russellmitchell is the weak fold — the raw DNS-count feature's within-testbed AUROC is 0.607 there vs.
0.93-1.00 on the other four development testbeds; see `table_feature_stability_stage3.csv`), and the pooled
confirmation-testbed AUROC is 0.729 (wilson 0.845, but **wheeler only 0.563 — close to chance**). In addition, because shaw's
calibration split has zero violated episodes, the isotonic calibrator fit on it collapses every posterior into a narrow
band near 1.0 (observed range [0.9956, 0.999999] on confirmation data): even where the underlying ranking is informative
(wilson), the calibrated decision is effectively constant, which is why every acquisition strategy including All-Evidence
gets uniform catastrophic loss on AIT-EXFIL confirmation data (Section 11 of `results/final_report_v3/RESULTS.md`). The
median development PR-skill of 0.998 that appears in the candidate-selection table reflects the high base rate of
violations in the development testbeds, not held-out ranking quality, and should not be read as evidence of strong
transfer.

This is reported as the actual outcome: **E1-AIT is not achieved by the frozen size-based role rule** for either claim.
AIT-INTRUSION fails only on sample support and would plausibly validate under a role assignment with more violated cases
in the target-A role; AIT-EXFIL's transfer is genuinely weaker and would likely remain unvalidated even with more
target-A samples, given the near-chance wheeler AUROC and the calibration collapse. The role rule is not changed post hoc;
a different pre-registered role assignment (e.g. rotating which testbed serves as target A, or a label-blind stratified
choice) is left as future work, since choosing it now would use confirmation-adjacent information not available before
the freeze.
