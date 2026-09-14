# Limitations

## What the evidence does not show
1. **No compliance or certification claim.** Testbed objectives are experimental operational predicates inspired by
   NIST SP 800-53/53A, NCA ECC-2:2024 and SCF; they are not legal interpretations. AIT/CERT labels are attack/insider
   micro-claims, not compliance labels.
2. **No human-auditor comparison** and **no real organisational cost**: acquisition costs are records/bytes/seconds
   measured on a local testbed and SQLite replay stores; privacy exposure is a category-count proxy.
3. **Synthetic-but-live organisations.** The IAM testbed runs real Keycloak/PostgreSQL/Linux state, but the scenario
   distribution (violation mechanisms, documentation maturity, staleness) was designed by the authors of this
   prototype. Results depend on that distribution; real enterprises may differ in prevalence, evidence reliability and
   source costs. Organisational history is emulated by time-shifting event timestamps.

## Findings that limit the contribution (from held-out results)
4. **Efficiency, not lower loss.** AVOI-GRC used significantly fewer acquisitions and lower cost than checklist, random,
   cheapest-first, confidence-threshold, information-gain, lookahead and all-evidence strategies on the IAM testbed,
   but its expected decision loss was **significantly higher** than greedy information gain (+0.028) and all-evidence
   acquisition (+0.065) there, and not significantly different from most other baselines. In AIT its loss was higher
   than the random-order baseline and the myopic cost-sensitive VOI. The λ/μ/ν penalties trade decision quality for
   acquisition economy; the declared weights determine where on that frontier AVOI operates.
5. **Safety improvements are concentrated against symmetric-loss VOI.** AVOI's unsafe assurance rate was significantly
   lower than generic symmetric VOI (B5) on all datasets and lower than confidence-threshold, lookahead and random
   baselines on CERT only; it was not significantly lower than information gain, fixed checklist or all-evidence on
   any dataset, and it was significantly higher than random order and cheapest-first on AIT.
6. **Escalation mainly prevents false non-assurance (H5 caveat).** In the IAM conflicting-evidence subset, escalation
   reduced unsafe *autonomous* decisions, but the no-escalation variant produced fewer false assurances because, under
   the 10:2 loss, it defaults to NotAssured when uncertain (AVOI 7 vs 2 false assurances, exact McNemar p = 0.0625;
   91 vs 310 false non-assurances; n = 1,338 episodes).
7. **Pre-registration flaw (deviation D1).** The registered safety-target matching for H1/Table 5 was degenerate
   (thresholds that never assure satisfy any UAR target at zero cost). H1 is therefore not supported as registered;
   the non-degenerate post-hoc analysis is exploratory and cannot confirm the hypothesis.
8. **Cross-testbed transfer failure on AIT.** The evidence model trained on one AIT testbed is badly miscalibrated on
   the other (full-evidence ECE ≈ 0.26, calibration slope ≈ 0.19); many false assurances occur with terminal belief
   ≥ 0.95. Degrading network-observation evidence *reduced* loss, i.e. those sources were misleading under shift. AIT
   results mostly reflect distribution shift shared by all methods. AIT-INTRUSION has only 12 refuted windows.
9. **Coverage-target matching was imprecise** (inner-validation coverage grid too coarse; many folds "partially
   achieved"), weakening the H3 tests; risk–coverage curves are descriptive.
10. **Sensitivity to source reliability.** Degrading reconciliation evidence at evaluation time raised IAM loss from
    0.421 to 1.061 on the affected episodes (configuration state: 0.178 → 0.666), and degrading CERT device activity
    raised loss from 0.441 to 1.315: the policy relies heavily on a few decisive sources and the fitted model does not
    detect reliability shift. In the IAM dormancy objective AVOI selected a single source in every episode.
11. **Myopic selection.** AVOI is myopic; a two-step lookahead did not reduce loss on IAM/AIT and was worse on CERT, but
    richer non-myopic POMDP planners were not evaluated.

## Data and protocol limitations
12. **Only two public datasets.** Splunk BOTS v3 (answer key e-mail gated; proprietary index format) and LANL cyber1
    (e-mail form gated) were not used, so the "≥ 3 public datasets" target and the random-effects meta-analysis were not met.
13. **CERT case-control sampling** (all insider weeks + sampled clean weeks) inflates prevalence; reweighted results in
    Table 9 are importance-weighted re-summaries, not re-runs.
14. **AIT claim definitions** were chosen after inspecting label temporal prevalence (before running methods).
15. **Discretisation of public evidence** into no-data/low/elevated/high by training quantiles discards information and
    favours none of the methods specifically, but a richer evidence model could change absolute performance.
16. **LLM planner** evaluated on one fold of the IAM testbed with a single 8B local model; it acquired nearly all evidence.
17. **Execution environment:** Windows Smart App Control forced older package versions; results were produced on one
    machine; wall-clock costs are hardware-dependent (evidence-count metrics are provided as hardware-independent
    alternatives).
