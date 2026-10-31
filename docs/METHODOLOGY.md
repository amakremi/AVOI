# Methodology

## Problem formulation
For an atomic objective or micro-claim c, Y_c ∈ {0,1} (1 = satisfied/claim holds). With acquired evidence E_t the
agent maintains b_t = P(Y=1 | E_t) from a probabilistic evidence model fitted on training folds only (never an LLM
self-report). Terminal decisions: Assured, NotAssured, HumanReview.

**Loss** (`config/loss_matrix.yaml`, experimental utility parameters, not financial/regulatory values):
L(Assured, Y=0)=10, L(NotAssured, Y=1)=2, L(HumanReview, ·)=1, correct autonomous decision 0; sensitivity FA ∈
{2,5,10,20}. Bayes risk R(b) = min_d Σ_y L(d,y) P(y).

**AVOI** (`src/avoi/avoi.py`): for available action a with outcomes o,
E[R_{t+1}|a] = Σ_o P(o|E_t,a) R(P(Y|E_t,o,a)); ΔR(a) = R(b_t) − E[R_{t+1}|a];
AVOI(a) = ΔR(a) − λC(a) − μP(a) − νD(a), with λ=0.05, μ=0.02, ν=0.02 declared a priori. a* = argmax AVOI. Stop when
R(b_t) ≤ τ (autonomous decision) or max AVOI ≤ 0 / no action left (HumanReview if R(b_t) > τ). Reliability enters
through the learned likelihoods, not as a bonus.

**Agent loop** (`src/avoi/agent.py`): objective → acquired evidence → legal actions → posterior → risk → AVOI of every
action → select → invoke evidence tool (access-controlled `EvidenceEnvironment`) → append observation/provenance →
update → acquire/decide → JSON trace (initial belief, candidates with expected outcomes and AVOI values, selected
action, observed outcome, updated belief/risk, final decision/loss, cost, privacy, delay, stop reason).

## Evidence models (`src/avoi/models`)
* **Primary — TAN** (Chow–Liu tree over conditional mutual information, Dirichlet α ∈ {0.5,1,2,5} chosen by inner-CV
  masked log loss), exact sum-product inference under missing evidence (verified against brute-force enumeration).
* **Secondary — calibrated logistic regression** with random-mask augmentation, isotonic (≥1,000 rows) or sigmoid
  calibration with calibration folds grouped by episode; one calibrated multinomial model per action for P(O_a|E).
* Ablation models: Naive Bayes; fixed global reliability (no per-source reliability learning).

## Costs, delay, privacy (`src/avoi/costs.py`)
Regime A uniform (1 per action); Regime B = ½·records/max + ½·bytes/max (training-fold normalisers); delay = measured
seconds / training max; privacy exposure = |sensitive categories in the payloads actually accessed| / 10 (proxy).
Measured seconds/bytes are testbed measurements, not organisational audit costs.

## Baselines (all share the evidence model, cost model and — unless stated — the asymmetric decision layer)
B0 all evidence (Bayes decision incl. escalation) · B1 fixed checklist (config order; risk-threshold stop) · B2 random
order (20 seeds) · B3 cheapest first · B4 greedy information gain (entropy reduction; ε=0.001 bits) · B5 generic VOI
(symmetric 0–1 loss minus λ·cost; no escalation, no privacy) · B6 confidence threshold (fixed order; stop at
max(b,1−b) ≥ θ; escalate when exhausted) · B7 myopic cost-sensitive VOI (asymmetric misclassification loss, no reject
option; *in the style of* myopic VOI feature acquisition, not a reproduction of a specific paper) · B7b two-step
lookahead VOI (approximate non-myopic/POMDP-style planning) · B8 LLM-only planner (llama3.1:8b via Ollama, secondary,
IAM outer fold 0).

## Evaluation protocol
* Nested CV (`config/hyperparameters.yaml`): IAM outer StratifiedGroupKFold(5) over scenario families, inner
  GroupKFold(3); AIT leave-one-testbed-out, inner 3 contiguous time blocks; CERT StratifiedGroupKFold(5) over users,
  inner (3). Robustness: IAM leave-one-family-out (40 folds).
* Every threshold is tuned on inner validation by J = mean loss + λ·cost + μ·privacy + ν·delay; target-matched points
  are selected on inner validation; curves are descriptive over held-out thresholds.
* Operating points for any threshold/budget are obtained by exact truncation of full trajectories (unit-tested).
* Conditions: cold start (primary); initial missingness 20/40/60/80% × {MCAR, source block, adversarial = hide top
  training-MI sources}; reliability degradation (50% outcomes of one source category replaced by training marginals at
  evaluation, no retraining); action-cost change (×5 per source category); prevalence reweighting (10/25/50%).
* Statistics (`src/avoi/evaluation/metrics.py`): stratified bootstrap 5,000; Wilcoxon + rank-biserial; exact McNemar;
  sign-flip permutation (random baseline); Holm; Friedman with Kendall's W.

## Testbed time shifting
Keycloak records events with the current clock. To emulate history, event and admin-event timestamps and user
creation timestamps are shifted in PostgreSQL immediately after each audited operation (identified by event-ID sets,
not clock comparison). The assessment time T0 is taken from the database clock after setup; every evidence collector
and the oracle only consider events strictly before T0, so login tests executed during assessment never affect
evidence or labels.

## Deviations
The non-degenerate matched-safety analysis is exported in `results/tables/table5b_matched_safety_nondegenerate.csv`;
it is a post-hoc exploratory analysis and does not replace the registered comparison.
