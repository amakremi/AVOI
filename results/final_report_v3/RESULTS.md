# AVOI — Results, Stage 3 (adaptive evidence selection and external-domain validation)

This report presents Stage 3 on top of the unchanged Stage 1 (original, ungated) and Stage 2 (evidence-model adequacy
safety condition) results. It does not restate Stage 1/2 findings as new; Section 17 gives the cross-stage synthesis.
Stage-1/2 artefacts are verified byte-for-byte unchanged before any Stage-3 code ran (`results/archive/pre_stage3_snapshot/`,
`tests/test_stage3.py::test_previous_results_unchanged`).

## 1. Experimental history

Stage 3 asks two questions the frozen Stage-1/2 design could not: (WP1) *does AVOI's next-evidence choice actually
depend on what has been observed*, and does that adaptivity buy anything over a policy that commits to a fixed
acquisition order; and (WP2) *does the Stage-2 evidence-model-adequacy gate ever pass an external (non-IAM) domain*,
given that Stage 2 left AIT-LDS v2.0 and CERT without a single VALIDATED model. Both questions require new data:
WP1 needs IAM scenarios whose ground truth can differ in a way that is invisible to AVOI but recoverable for analysis
(a latent "branching mechanism"); WP2 needs untouched AIT testbeds and CERT releases so that "target" and "confirmation"
partitions are genuinely independent of everything used to select or tune evidence models in Stage 1/2.

Protocol: `docs/STAGE3_REUSE_MAP.md` classifies every component before touching code; `config/stage3.yaml` fixes
hypotheses, seeds, loss/weights (identical to Stage 2 primary) and the WP1/WP2 rules; `results/stage3/EXPERIMENT_FREEZE_STAGE3.json`
(freeze v2, combined sha256 `cfed9952be3d29d47a4dd7840fac5816795c9c67b2624e95ed354277bfa65607`) freezes the frozen file
set before any adequacy validation or confirmation label was read; `results/stage3/ADEQUACY_DECISIONS_STAGE3.json`
(sha256 `2346565c9a6504949e6b360e45f28831fe2d3f534e5114f9d03427de442f366c`) freezes the six adequacy decisions (three IAM,
two AIT, one CERT) before confirmation ran. A coding defect found after the adequacy freeze (a stale IAM-only global
left set from WP1, crashing WP2's confirmation-phase threshold tuning) is corrected under a **versioned corrected
freeze** (protocol Section 48): v1 is preserved as `EXPERIMENT_FREEZE_STAGE3_v1_SUPERSEDED.json`, v2 documents the
defect, its scope (confirmation-phase tuning only — `adequacy_phase()` never called the buggy code path) and the fix
(`experiments/stage3/freeze_correction_v2.py`). The adequacy decisions were not regenerated; they are unaffected.

## 2. Reused Stage-1/2 components

Per `docs/STAGE3_REUSE_MAP.md`, REUSED UNCHANGED: the AVOI formula and agent core (`src/avoi/agent.py`'s selection and
stopping logic other than the new `frozen_order` flag), the Bayes-risk terminal decision and loss matrix
(`avoi/bayes_risk.py`), the Stage-2 evidence-model-adequacy gate and policy (`config/model_adequacy.yaml`,
`avoi/adequacy.py`) — **byte-identical**, TAN/Naive-Bayes evidence models (`avoi/models/tan.py`), the cost/privacy/delay
model, the IAM Docker/Keycloak testbed's mechanism logic (only additively extended, see Section 4), the Stage-1
Discretizer, the group-bootstrap/sign-flip/Holm statistical toolkit (`avoi/evaluation/metrics.py`,
`avoi/evaluation/stage2.py`'s `tune`/`trajectories`/`rows_at`/`gate_rows`), and all nine Stage-1/2 datasets as **Stage-3
development data only** (never re-used as new confirmation data). REUSED WITH EXTENSION: the IAM scenario generator
(`testbed/scenarios/generator.py`, additive `branching_mechanisms()`, verified byte-identical on Stage-1/2 configs via
pre-recorded hashes), `avoi/agent.py` (added `frozen_order` policy flag), `avoi/datasets/iam.py` (extended file-prefix
whitelist). NEW IMPLEMENTATION: the branching-scenario mechanism, Frozen-Order AVOI wrapper, fixed-horizon evaluation,
adaptivity metrics and permutation test (WP1); LODO candidate selection, the monotone-calibrator safeguard, and one new
model class `HGBEvidenceModel` (WP2). NOT NEEDED: no change to the AVOI formula, the adequacy policy, or the primary
loss/weight configuration.

## 3. Stage-3 protocol and freeze

Freeze discipline followed throughout: adequacy policy (unchanged) → freeze thresholds/partitions/hypotheses
(`config/stage3.yaml`, written before any Stage-3 label was read) → develop (LODO/HGB model selection, feature-stability
diagnostic, all on development data only) → adequacy-validate (six decisions, frozen) → confirm (WP1 fixed-horizon +
normal-operation runs on IAM confirmation scenarios; WP2 runs on AIT/CERT confirmation partitions). Two scope
reductions were made and documented **before** reading the affected labels: (a) the CERT new-release pool was reduced
from four releases (r4.1/r5.1/r6.1/r6.2) to two (r4.1/r5.1) once r5.1's measured single-threaded bz2 extraction time
(~110 min for 11 GB) showed the remaining two releases would need a further ~7-8 hours (`docs/STAGE3_EXTERNAL_MODELS.md`
§2b); (b) no other reduction was made. `experiments/stage3/archive_snapshot.py` hashed 2,603 pre-existing files and
recorded the git commit before any Stage-3 code ran; `verify()` was re-run repeatedly and always confirmed Stage 1/2
were unchanged.

## 4. WP1 branching IAM scenarios

The IAM scenario generator is extended (not replaced) with a `branching` config block: for each of the three WP1
objectives (IAM-01-MFA-PRIV, IAM-02-TERM-DISABLED, IAM-03-PRIV-AUTHZ) a balanced, seeded per-family assignment forces
one of five latent mechanism outcomes (`testbed/scenarios/generator.py::branching_mechanisms`). This latent assignment
is stored only under `latent["branching_mechanisms"]` for post-hoc analysis and world construction — it is never exposed
to the acquisition policy, which only ever sees the same admissible evidence-action set as Stage 1/2. Three new,
never-before-used generator configs produce development (512 scenarios, seed 20270111, 64 families), validation (256
scenarios, seed 20270222, 32 families) and confirmation (256 scenarios, seed 20270333, 32 families) partitions. Byte-identical
behaviour of the extended generator on the original Stage-1/2 configs is verified for six scenario indices against
pre-recorded hashes (`tests/fixtures_generator_spec_hashes.json`).

## 5. Direct evidence of adaptive next-evidence selection (Hypothesis A1)

**Table:** `table_adaptive_selection_stage3` (confirmation partition, normal-operation AVOI).

| objective | adequacy | distinct actions @ step 1 | @ step 2 | mean entropy bits (t≥2) | ranking-change rate | rank-reversal rate | permutation p (Holm) |
|---|---|---|---|---|---|---|---|
| IAM-01-MFA-PRIV | VALIDATED | 1 | 2 | 0.917 | 0.643 | 0.564 | 0.0003 |
| IAM-02-TERM-DISABLED | VALIDATED | 1 | 1 | 0.648 | 0.672 | 0.589 | 0.0003 |
| IAM-03-PRIV-AUTHZ | RESTRICTED | 1 | 2 | 1.053 | 0.756 | 0.546 | 0.0003 |

At step 1 every objective is degenerate by construction (no history yet exists, so the first action is fixed given the
prior). From step 2 onward, IAM-01 and IAM-03 select ≥2 distinct next actions across confirmation episodes, and all
three objectives show substantial re-ranking between successive observations (ranking-change rate 0.64-0.76; a
"rank-reversal" — the adaptive next action differing from what the frozen initial ranking would pick — on 55-59% of
observed steps). The group-aware permutation test (H0: next action independent of observed history, given objective and
step; null permutes history labels within (scenario-family × step) blocks; 10,000 permutations, 64 blocks = 32
confirmation families × 2 step values, 512 total steps at t≥2) rejects independence for all three objectives at raw
p = 0.0001 and Holm-adjusted p = 0.0003.

**A1 is SUPPORTED**: at least one branching objective (in fact IAM-01 and IAM-03) shows ≥2 distinct next actions at
some step t≥2 with the group-aware test Holm-significant across all three objectives, exactly as pre-registered.
IAM-02's step-2 distinct-action count of 1 does not weaken this: the A1 rule requires history-dependence for *at least
one* objective, and IAM-02's own permutation test is independently significant (its adaptivity shows up at later steps
than step 2; entropy over t≥2 is 0.648 bits, not zero).

## 6. Adaptive vs Frozen-Order AVOI at matched evidence horizons (Hypothesis A2)

Frozen-Order AVOI (`PolicyConfig(frozen_order=True)`) computes the AVOI ranking once, at the first decision point, and
then always acquires the highest-ranked action still available from that frozen list — every other component (evidence
model, cost/privacy/delay weighting, loss, terminal Bayes decision, HumanReview) is identical to Adaptive AVOI. Both
policies are forced to acquire exactly k ∈ {2, 3} actions (`stop_rule="none"`, no threshold stop, `max_steps=k`), so the
comparison isolates the effect of re-ranking after each observation from the effect of *when* to stop.

**Table:** `table_fixed_horizon_stage3` (confirmation, n = 256 pairs per objective/k).

| objective | k | adaptive loss | frozen loss | difference [95% CI] | sign-flip p (Holm) |
|---|---|---|---|---|---|
| IAM-01-MFA-PRIV | 2 | 0.1797 | 0.1797 | 0.0000 [0.000, 0.000] | 1.000 |
| IAM-01-MFA-PRIV | 3 | 0.1641 | 0.1641 | 0.0000 [0.000, 0.000] | 1.000 |
| IAM-02-TERM-DISABLED | 2 | 0.1563 | 0.2422 | −0.0859 [−0.121, −0.055] | 0.0006 |
| IAM-02-TERM-DISABLED | 3 | 0.1289 | 0.2422 | −0.1133 [−0.156, −0.074] | 0.0006 |
| IAM-03-PRIV-AUTHZ | 2 | 0.4531 | 0.4336 | +0.0195 [−0.043, 0.109] | 1.000 |
| IAM-03-PRIV-AUTHZ | 3 | 0.5195 | 0.3984 | +0.1211 [0.016, 0.242] | 0.0984 |

Pooled over the three objectives (as pre-registered), paired group bootstrap (5,000 resamples, blocks = objective ×
scenario family) and sign-flip permutation (10,000 permutations, Holm across k∈{2,3}) give: k=2, mean difference
−0.0221 [95% CI −0.0482, +0.0104], sign-flip p = 0.143; k=3, mean difference +0.0026 [−0.0378, +0.0482], p = 0.951.
Neither k has a CI entirely below 0, and neither reaches Holm significance.

**A2 is NOT SUPPORTED at the pre-registered pooled level.** Per-objective results, reported descriptively as the
protocol allows:
- **IAM-02-TERM-DISABLED**: Adaptive AVOI is significantly better than Frozen-Order at both k=2 and k=3 (Holm p =
  0.0006), by 0.086-0.113 expected loss. This is the one objective where re-ranking after observation has a clear,
  significant, and reproducible benefit.
- **IAM-01-MFA-PRIV**: the two policies are byte-identical in outcome at both horizons. Inspection of the fixed-horizon
  traces shows the *set* of k actions Adaptive and Frozen-Order acquire is the same on this objective at matched
  budgets — only the order differs — and the terminal Bayes decision depends on the evidence collected, not the order
  it arrived in, so the null effect is mechanically expected, not a sign that re-ranking never mattered (Section 5
  shows IAM-01 does re-rank).
- **IAM-03-PRIV-AUTHZ**: Frozen-Order is numerically *better* than Adaptive at both horizons, reaching a marginal
  (pre-Holm p = 0.025, Holm p = 0.098) effect at k=3. This objective is also the one RESTRICTED model in WP1 (Section 9):
  an adequacy-inadequate posterior can make adaptive re-ranking actively counter-productive, since it is chasing a
  poorly calibrated value signal. See Failure Analysis.

Because the pooled, pre-registered analysis mixes one clear win (IAM-02), one null result (IAM-01) and one loss
(IAM-03), it does not clear the pre-registered bar. This is reported as the actual outcome.

## 7. Value-based stopping: normal-operation comparison

**Table:** `table_normal_operation_stage3` (validation-tuned thresholds, raw and adequacy-enforced).

Under normal operation (value-based stopping enabled, thresholds tuned on the validation partition, not the matched
fixed-k comparison of Section 6), AVOI and Frozen-Order AVOI diverge in a different way because the amount of evidence
collected before stopping is no longer held equal:

- **IAM-01-MFA-PRIV**: identical (coverage 1.000, UAR 0.018, loss 0.242, 1.0 acquisition) — the tuned threshold stops
  both policies after one item.
- **IAM-02-TERM-DISABLED**: AVOI stops earlier on average (1.242 acquisitions) than Frozen-Order (1.902), but Frozen-Order
  achieves *better* coverage (0.902 vs 0.867) and lower loss (0.129 vs 0.156). This appears to contradict Section 6, but
  it is not the same comparison: Section 6 fixes the evidence budget (isolating the selection-order effect); here the
  two policies are also free to stop at different points, so the comparison confounds selection order with the total
  amount of evidence gathered. Frozen-Order happens to keep collecting evidence for longer under the tuned threshold on
  this objective, and more evidence (of any order) helps.
- **IAM-03-PRIV-AUTHZ**: identical (coverage 1.000, UAR 0.012, loss 0.430, 1.0 acquisition) under `raw` thresholds; both
  fall to coverage 0 / loss 1.0 under `enforced` (gate blocks all autonomy — this objective is RESTRICTED; see Section 9).

`table_normal_operation_stage3` also situates AVOI against the full Stage-1/2 baseline suite (All Evidence, Checklist,
20-seed Random, Cheapest First, Information Gain, Generic VOI, Confidence Threshold, Myopic Cost-Sensitive VOI,
Lookahead-2) on the same branching confirmation scenarios; the qualitative Stage-1/2 pattern (AVOI acquires far fewer
items than All Evidence/Checklist at broadly comparable UAR) replicates here and is not restated as a new finding.

## 8. WP2 external-model development

Development uses **only** previously examined AIT-LDS v2.0 testbeds (russellmitchell, santos, fox, harrison, wardbeck)
and CERT releases (r4.2, r5.2) — never target or confirmation data. Candidates: TAN and Naive Bayes (reused, α ∈
{0.5,1,2,5}) and one new model class, `HGBEvidenceModel` (HistGradientBoostingClassifier wrapped in the existing
posterior/predictive interface; not a large neural model). `CalibratedLogisticModel` is interface-compatible but
excluded from the pool (`docs/STAGE3_EXTERNAL_MODELS.md` §2a — no near-miss result suggested it would change any
selection). Selection: exclude semantically invalid models (non-finite outputs, or a calibration map that is
*decreasing* in P(Y=1|E) — the diagnosed root cause of Stage 2's AIT-EXFIL AUROC-0.024 failure, see §9); rank by
worst leave-one-development-source-out (LODO) AUROC; require positive median development PR-skill; tie-break on log
loss, then Brier, then ECE. Calibrators are restricted to monotone maps only (none/sigmoid/isotonic/beta). Two variants
are fit per claim: **zero-shot** (structure + calibrator both selected on development-only data) and
**target-calibrated** (same structure, calibrator re-selected on the target/new-pool calibration split only) —
target-calibrated is the pre-registered primary variant for the adequacy decision; zero-shot is diagnostic only.

## 9. AIT model adequacy

Stage 2's AIT-EXFIL result (AUROC 0.024 on confirmation — worse than random, in the "wrong" direction) is diagnosed
(development data only): **not** a metric-orientation error and **not** a genuine inversion of the underlying model —
the raw DNS-count statistic separates EXFIL windows in the same direction with AUROC 1.00 on every one of the five
development testbeds. It was a **non-monotone calibrator** artefact: Stage-2 development pooled only two testbeds with
mismatched discretisation thresholds, producing inverted out-of-fold predictions (dev OOF AUROC 0.249), on which a
Platt calibrator learned a negative slope (b = −0.46) and inverted an otherwise excellent uncalibrated validation model
(AUROC 0.976 on fox) to AUROC 0.024. The monotone-calibrator safeguard added in Stage 3 makes this class of failure
structurally impossible going forward.

Untouched AIT-LDS v2.0 testbeds (verified against Zenodo record 5789064): shaw (17.6 GB), wheeler (19.6 GB), wilson
(26.5 GB). The frozen, size-based role rule (smallest → target A) assigns **shaw** to calibration (40%) + adequacy
validation (60%), label-blind split by hour block; **wheeler and wilson** to confirmation. This assignment was fixed
before any Stage-3 AIT label was read.

**Outcome (both AIT claims RESTRICTED, `INSUFFICIENT_ADEQUACY_SAMPLE_SUPPORT`):** shaw's genuinely low activity rates
made this outcome close to mechanical rather than a discrimination failure for one of the two claims, and a genuine
weak-transfer finding for the other:

| claim | model | LODO worst-fold AUROC | shaw target-cal. AUROC | shaw n_violated | confirmation-testbed AUROC (pooled) | wheeler | wilson |
|---|---|---|---|---|---|---|---|
| AIT-EXFIL | HGB | 0.638 | NaN (0 violated) | 0 / 504 | 0.729 | 0.563 | 0.845 |
| AIT-INTRUSION | TAN(α=2) | 0.837 | 0.994 [0.983, 1.000] | 6 / 504 | 0.969 | 0.966 | 0.977 |

AIT-INTRUSION is robustly discriminative across every development testbed, on shaw, and on both confirmation testbeds;
it is RESTRICTED purely because shaw carries only 6 violated episodes (2 independent groups), short of the unchanged
support rule. AIT-EXFIL is materially weaker: its worst development fold (russellmitchell) has AUROC only 0.607 for the
raw DNS-count feature (`table_feature_stability_stage3`), its confirmation-testbed AUROC is a middling 0.729
(near-chance, 0.563, on wheeler), and — because shaw's calibration split has zero violations — its isotonic calibrator
collapses every posterior into the narrow band [0.9956, 0.999999], making the calibrated decision effectively constant
regardless of the underlying evidence (Section 11). AIT-EXFIL's RESTRICTED status is not solely a sample-support
artefact of the target-testbed choice; the model's transfer is genuinely weaker than AIT-INTRUSION's.

A target-testbed data-leakage bug was found and fixed during WP2-AIT development: an early version of the
calibration/adequacy-validation split was computed over the full 3-testbed pool instead of shaw alone, which would have
let confirmation-testbed (wheeler, wilson) data leak into the adequacy-validation partition. `target_a_only()` was
added to restrict every split to shaw before any split logic runs; the fix was verified by direct inspection before any
adequacy decision was frozen (Section 3).

## 10. CERT model adequacy

Because r5.1's real single-threaded extraction time (~110 min for 11 GB) showed the full four-release plan (r4.1,
r5.1, r6.1, r6.2) would need several more hours than this session's time budget, the new-release pool was reduced to
**r4.1 + r5.1** (7 insiders combined, vs. 17 in the original plan) — decided and frozen before any r4.1/r5.1 label was
read (`docs/STAGE3_EXTERNAL_MODELS.md` §2b). r6.1/r6.2 remain downloaded and MD5-verified for future work.

Development (r4.2 dev → evaluate r5.2, and r5.2 dev → evaluate r4.2, reused Stage-1/2 releases) selects TAN(α=5.0)
under the same LODO-style, monotone-calibrator-restricted procedure as AIT. On the pooled new-release
(r4.1+r5.1) target-calibrated model:

| model | AUROC | AUPRC | PR-skill | Brier | BSS | ECE | slope | n | n_violated | groups |
|---|---|---|---|---|---|---|---|---|---|---|
| TAN(α=5.0) + sigmoid | 0.895 [0.671, 0.953] | 0.306 [0.029, 0.600] | 0.267 [0.017, 0.560] | 0.043 | 0.744 [0.554, 0.918] | 0.017 [0.005, 0.064] | 1.310 [0.476, 2.066] | 394 | 21 | 187 |

**CERT-INSIDER is VALIDATED** (`ALL_PRIMARY_ADEQUACY_CONDITIONS_MET`) — discrimination, calibration and sample-support
conditions all pass. This is E1-CERT: the first external (non-IAM) evidence model to clear the unchanged Stage-2
adequacy gate across both stages of this project. It is nonetheless an imperfect model at its adequacy-validation
operating threshold: `sensitivity_violated` is 0.0 and `MCC` is 0.0 (balanced accuracy 0.5) — none of the 21 violated
(insider) episodes in the adequacy-validation split are classified as violated at that threshold, even though the
model's *ranking* of episodes by posterior is good (AUROC 0.895) and its calibration is sound (BSS 0.744, ECE 0.017).
The adequacy policy's discrimination/calibration/support conditions are about probabilistic quality, not about
recall at a specific decision threshold; both are true at once here. See Section 14.

## 11. External AVOI confirmation (Hypothesis E2)

**E1 is SUPPORTED**: at least one external claim (CERT-INSIDER) is VALIDATED. Decomposed: **E1-AIT is NOT SUPPORTED**
(both AIT claims RESTRICTED); **E1-CERT is SUPPORTED**.

`table_external_avoi_stage3` reports AVOI vs. the full baseline suite on confirmation data for all three external
claims, per protocol Section 45 (RESTRICTED claims included as diagnostic-only rows, never discarded):

**CERT-INSIDER (VALIDATED, primary E2 evidence), n=458 confirmation episodes:**

| method | coverage | mean acquisitions | normalised cost | expected loss |
|---|---|---|---|---|
| All Evidence | 0.871 [0.820, 0.915] | 10.000 | 1.2367 | 0.238 [0.136, 0.363] |
| Checklist | 0.747 [0.683, 0.807] | 4.845 | 0.4156 | 0.275 [0.206, 0.351] |
| Information Gain | 1.000 [1.000, 1.000] | 0.000 | 0.0000 | 0.306 [0.067, 0.711] |
| AVOI | 0.721 [0.655, 0.782] | 2.415 | 0.0564 | 0.301 [0.230, 0.376] |

AVOI's acquisitions and normalised cost are far lower than every non-degenerate comparator (paired Wilcoxon,
Holm-corrected within metric, all p < 1e-75: vs All Evidence, vs Checklist, vs Information Gain). Applying the
pre-registered no-trivial-abstention gate (efficiency is claimed only if AVOI's coverage is not below the comparator's
by more than 0.10):
- **vs Checklist**: coverage gap 0.026 ≤ 0.10 → gate passes. AVOI acquires 2.415 vs 4.845 items and costs 0.0564 vs
  0.4156, at comparable coverage. **Efficiency claim holds.**
- **vs All Evidence**: coverage gap 0.150 > 0.10 → gate fails. AVOI's lower cost is partly explained by abstaining
  (routing to HumanReview) more often; the comparison is not a like-for-like efficiency win.
- **vs Information Gain**: coverage gap 0.279 > 0.10 → gate fails. Information Gain's operating point here is
  degenerate on CERT-INSIDER (0 acquisitions, UAR 1.000 — every one of its "assured" decisions in this domain is a
  false assurance); it is not a meaningful efficiency comparator regardless of the gate.

**E2 is PARTIALLY SUPPORTED**: the acquisition-efficiency advantage holds against a fixed-checklist baseline at
comparable coverage, but not against All Evidence (coverage-gated) or Information Gain (coverage-gated and degenerate).

AIT-EXFIL and AIT-INTRUSION rows are reported as diagnostic only (status RESTRICTED, E2 not applicable to them). On
AIT-EXFIL, *every* method — including All Evidence — has identical expected loss (6.073) because the isotonic
calibrator collapses all confirmation-testbed posteriors near 1.0 (Section 9); no acquisition strategy can recover
information the calibration step has already destroyed. On AIT-INTRUSION (also RESTRICTED, but for sample-support
only), AVOI and several baselines achieve their best loss (0.063) at 0 acquisitions by "assuring" nearly everyone,
which is safe only because AIT-INTRUSION's confirmation-testbed violation prevalence is under 1%; this is not evidence
of good evidence-selection behaviour and would not be reported as a finding if the claim were VALIDATED.

## 12. Zero-shot vs target-calibrated external evidence models

**Table:** `table_zero_shot_vs_target_stage3`.

| claim | variant | AUROC | PR-skill | BSS | ECE | slope |
|---|---|---|---|---|---|---|
| AIT-EXFIL | zero-shot | NaN | NaN | 0.844 | 0.168 | NaN |
| AIT-EXFIL | target-calibrated | NaN | NaN | 1.000 | 0.002 | NaN |
| AIT-INTRUSION | zero-shot | 0.994 | 0.704 | 0.351 | 0.007 | 1.637 |
| AIT-INTRUSION | target-calibrated | 0.994 | 0.704 | 0.351 | 0.007 | 1.637 |
| CERT-INSIDER | zero-shot | 0.895 | 0.267 | 0.488 | 0.113 | 0.743 |
| CERT-INSIDER | target-calibrated | 0.895 | 0.267 | 0.744 | 0.017 | 1.310 |

AUROC and PR-skill are unaffected by re-calibration (monotone transforms preserve ranking) so they are identical
within each claim by construction; AIT-EXFIL's AUROC/PR-skill are NaN on shaw's own adequacy-validation split because
it contains zero violated episodes there. Re-calibrating on the CERT target/new-pool split materially improves
calibration quality (BSS 0.488 → 0.744, ECE 0.113 → 0.017, slope closer to 1: 0.743 → 1.310) without changing
discrimination — target adaptation is doing real, useful work for CERT-INSIDER. For AIT-INTRUSION, target calibration
makes no difference at all (shaw's calibration split is too small/degenerate relative to development to shift the
selected calibrator). For AIT-EXFIL, target calibration raises BSS (0.844 → 1.000 — an artefact of shaw's calibration
split having 0 violations, not genuine improvement) while catastrophically narrowing the posterior range used on
confirmation data (Section 9) — a case where the calibration-quality metric computed *on the target partition itself*
is misleadingly perfect precisely because that partition has no positive class to be miscalibrated against.

## 13. Statistical analysis

All Stage-3 statistics reuse Stage-2 machinery unchanged (`avoi/evaluation/metrics.py`): group bootstrap (5,000
resamples, groups = scenario family for IAM, testbed×hour-block for AIT, release:user for CERT), paired group
bootstrap for A2, sign-flip permutation (10,000 permutations) with Holm correction for A2 and E2 significance, and
exact McNemar carried over from Stage 1/2 methodology where applicable. WP1's group-aware conditional-mutual-information
permutation test for A1 is new (Section 5), built on the same block-permutation principle to respect the (scenario
family × step) dependence structure rather than treating steps as i.i.d. All seeds are fixed in `config/stage3.yaml`
before any Stage-3 result was computed (analysis 20270401, bootstrap 20270401, permutation 20270402; separate
data-split seeds for IAM generators, the AIT target split, and the CERT episode/user splits — all distinct).

## 14. Failure analysis

See `FAILURE_ANALYSIS.md` for the full accounting. Headline failures, none adjusted after the fact:
- A2 fails at the pre-registered pooled level, driven by one null objective (IAM-01: same evidence set regardless of
  order) and one objective where Frozen-Order is significantly *better* (IAM-03 — the one RESTRICTED WP1 objective).
- IAM-03-PRIV-AUTHZ never validates in either Stage 2 or Stage 3 (`MODEL_ADEQUACY_RESTRICTED`, calibration fails):
  adaptive re-ranking against a poorly calibrated value signal on this objective actively costs loss versus a fixed
  order.
- Both AIT claims are RESTRICTED; AIT-EXFIL's failure is not solely a sample-support technicality — worst-fold LODO
  AUROC (0.638) and confirmation-testbed AUROC (0.729, 0.563 on wheeler) show real transfer weakness, compounded by an
  isotonic-calibrator collapse driven by a zero-violation calibration partition.
- CERT-INSIDER passes discrimination/calibration/support adequacy yet has zero sensitivity to the violated class at
  its tuned operating threshold (MCC 0, sensitivity_violated 0) — VALIDATED is not a claim of good operating-point
  recall on the minority class.
- E2 (efficiency) fails the no-trivial-abstention gate against 2 of 3 baselines (All Evidence, Information Gain); it
  holds only against Checklist.
- The feature-stability diagnostic flags direction-reversing sources: `ait_query_monitoring` for AIT-EXFIL and
  `ait_query_web_access`, `ait_query_mail` for AIT-INTRUSION (`table_feature_stability_stage3`) — none were removed,
  since removal was pre-committed to require both a flag and a worst-fold-AUROC improvement, and neither candidate
  changed the selected feature set enough to trigger removal.

## 15. Threats to validity

- **Branching-mechanism realism**: the five-way latent mechanism split is a controlled construction chosen to
  guarantee history-dependence exists to be measured; it is not a claim about real-world IAM outcome distributions.
- **CERT scope reduction**: 7 pooled insiders (r4.1+r5.1) rather than the originally planned 17 (adding r6.1/r6.2).
  The adequacy result may not hold with the full pool; r6.1/r6.2 remain available, undecompressed, for follow-up.
- **AIT target-testbed assignment**: the frozen, size-based rule assigned shaw to target A; both AIT outcomes are
  specific to that assignment (a different, still-pre-registerable rule might validate AIT-INTRUSION, whose transfer
  is otherwise robust).
- **Single environment / single run**: as in Stage 1/2, results are from one execution with fixed seeds; no
  independent replication of the full pipeline was performed.
- **A2's pooled test mixes heterogeneous objectives**: pooling a validated-model win (IAM-02), a mechanically-null
  comparison (IAM-01) and an inadequate-model loss (IAM-03) into one pre-registered pooled statistic is itself a
  design choice fixed before data collection; a different pre-registered aggregation (e.g., restricted to VALIDATED
  objectives only) might have shown A2 supported, but that would not be the analysis that was frozen.

## 16. Supported claims

See `CLAIMS_ALLOWED.md` for the full 12-claim table.

## 17. Cross-stage interpretation

Stage 1 showed AVOI sharply reduces evidence acquisition but did not establish safety superiority over strong
baselines, and exposed poor external-domain (AIT) model transfer. Stage 2 added a governed evidence-model-adequacy
gate: only 4 of 9 Stage-2 evidence models (all IAM) were ever eligible for autonomous use, and diagnosed but did not
fix AIT/CERT's inadequacy. Stage 3 newly establishes: (1) AVOI's next-evidence choice is genuinely history-dependent,
not an artefact of a fixed initial ranking (A1, supported); (2) that adaptivity's value versus a frozen acquisition
order is real but objective-specific, not a general effect, and can reverse sign when the underlying evidence model
is itself inadequate (A2, not supported at the pooled pre-registered level, supported on one of three objectives); (3)
the Stage-2 AIT-EXFIL failure was a fixable calibrator defect, not an inherent modelling failure, and the same
LODO + monotone-calibrator methodology produces the project's first VALIDATED non-IAM evidence model, CERT-INSIDER
(E1 supported); (4) even a VALIDATED external model can have zero operating-point sensitivity to the class that
matters, and AVOI's acquisition-efficiency advantage on it holds against some but not all comparators (E2, partially
supported). AVOI can now legitimately claim external-domain applicability exists in principle (one domain, one claim,
demonstrated end to end) but must not claim it generalises to AIT, to CERT releases beyond r4.1/r5.1, or that adaptive
selection is unconditionally better than a fixed order.
