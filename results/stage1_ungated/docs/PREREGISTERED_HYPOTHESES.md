# Pre-registered hypotheses (AVOI-GRC)

Written on 2026-09-14, **before** any final experiment was executed. The SHA-256 of this file is recorded in
`results/EXPERIMENT_FREEZE.json`; the final experiment runner refuses to run if the file changed after freezing.
Smoke tests executed during development (partial IAM data, ad-hoc split) were used only to debug code paths; no
design, grid, loss or hypothesis was changed on the basis of their numbers.

## Common definitions

* **Primary evidence layer:** Layer A — controlled IAM testbed (6 atomic objectives, 320 scenarios, 1,920 objective
  episodes). Layers B (AIT, CERT replay micro-claims) are **secondary/replication** evaluations of the same hypotheses.
* **Primary condition:** cold start (no evidence in hand), cost regime B, TAN evidence model, primary loss
  L(Assured|violated)=10, L(NotAssured|satisfied)=2, L(HumanReview)=1, preference weights λ=0.05, μ=0.02, ν=0.02.
* **Unit of analysis:** held-out episode (pooled over outer folds and objectives within a domain); all methods operate
  on the identical held-out episodes, so comparisons are paired.
* **UAR** = #(Assured ∧ Y=0) / #(Y=0). **Coverage** = fraction of episodes with an autonomous decision
  (Assured or NotAssured).
* **Tuned operating point:** threshold minimising J = mean loss + λ·cost + μ·privacy + ν·delay on inner validation.
* **Target-matched operating points:** thresholds selected on **inner validation only** (safety target: lowest
  mean cost with inner UAR ≤ target; coverage target: inner coverage closest to target within ±0.05).
* α = 0.05; Holm correction within each hypothesis family; effect sizes and 95% CIs (≥ 5,000 bootstrap resamples,
  stratified by label) are always reported. Statistical significance is not equated with practical superiority.

## H1 — acquisition efficiency at matched safety
*At matched unsafe-assurance risk, AVOI requires fewer evidence acquisitions than a fixed checklist.*

* Comparator: B1-FixedChecklist.
* Operating points: safety-target points UAR ≤ 1%, 2%, 5% (inner-selected) for both methods.
* Test: paired Wilcoxon signed-rank on per-episode acquisition counts (AVOI − B1) at each achievable target; Holm over
  targets achieved by both methods. Effect: rank-biserial correlation; bootstrap CI of the mean difference.
* **Supported** if, for at least the 5% target, AVOI's mean acquisitions are lower (Holm p < 0.05, CI of the mean
  difference < 0) **and** the upper 95% bootstrap bound of UAR(AVOI) − UAR(B1) on the held-out episodes is ≤ 0.02.
  **Not testable** for a target that either method does not achieve on inner validation ("not achieved").

## H2 — safety at matched evidence budget
*At matched evidence budget, AVOI has a lower Unsafe Assurance Rate than greedy information gain.*

* Comparator: B4-InformationGain (same evidence model, same decision layer).
* Operating points: tuned thresholds with hard acquisition budgets k = 1, 2, 3.
* Test: exact McNemar test on paired unsafe-assurance indicators among Y=0 episodes for each k; Holm over k.
  Summary effect: mean over k of UAR(AVOI) − UAR(B4) with bootstrap CI.
* **Supported** if the summary CI is entirely below 0 and at least one Holm-adjusted McNemar p < 0.05 with no budget
  where AVOI's UAR is significantly higher.

## H3 — risk–coverage trade-off
*AVOI provides a better risk–coverage trade-off than a confidence-threshold stopping strategy.*

* Comparator: B6-ConfidenceThreshold.
* Operating points: coverage-target points 60/70/80/90% (inner-selected); descriptive area under the held-out
  risk–coverage curve (UAR vs coverage) reported per fold.
* Test: exact McNemar on unsafe-assurance indicators (Y=0 episodes) at each coverage target achieved by both; Holm.
* **Supported** if AVOI has lower UAR at ≥ 2 of the achieved coverage targets with Holm p < 0.05 and is not
  significantly worse at any, **or** if UAR is not significantly different but AVOI achieves it with significantly
  fewer acquisitions (Wilcoxon, Holm) at ≥ 2 targets (reported as "supported via cost at equal safety").

## H4 — asymmetric assurance loss
*Assurance-specific asymmetric loss produces fewer unsafe assurance decisions than generic symmetric VOI.*

* Comparators: B5-GenericVOI (primary), A1-NoAsymmetricLoss (secondary, isolates the loss within AVOI).
* Operating points: tuned thresholds.
* Test: exact McNemar on unsafe-assurance indicators among Y=0 episodes; Holm over the two comparisons.
* **Supported** if UAR(AVOI) < UAR(B5) with Holm p < 0.05. Partially supported if only A1 is significant.

## H5 — explicit escalation
*Explicit escalation reduces unsafe autonomous decisions under conflicting or insufficient evidence.*

* Comparator: A6-NoEscalation.
* Subsets (defined before evaluation, label-free):
  * *conflicting evidence* (Layer A): episodes whose complete evidence vector contains at least one outcome whose
    nominal reading supports satisfaction and one supporting violation;
  * *insufficient evidence* (all domains): episodes whose posterior Bayes risk after acquiring ALL evidence
    (B0-AllEvidence final belief, same evidence model and fold) exceeds AVOI's tuned threshold for that fold,
    i.e. episodes in which even complete available evidence does not permit a sufficiently safe autonomous decision.
* Outcome: unsafe autonomous decisions = #(Assured ∧ Y=0) + #(NotAssured ∧ Y=1) per episode; and UAR.
* Test: exact McNemar on paired unsafe-autonomous indicators within each subset; Holm over the two subsets.
* **Supported** if AVOI has fewer unsafe autonomous decisions than A6 with Holm p < 0.05 in the conflicting-evidence
  subset.

## Not a hypothesis
Macro-averages across domains, cost regime A, the calibrated-logistic evidence model, the LLM planner, sensitivity
and robustness experiments are reported descriptively and cannot be used to claim support for H1–H5.
