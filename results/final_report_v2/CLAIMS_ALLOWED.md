# Claims allowed — AVOI (Stage 1 + Stage 2)

This file classifies 15 candidate claims about AVOI as SUPPORTED, PARTIALLY SUPPORTED or NOT SUPPORTED:
- **SUPPORTED:** the evidence holds for the stated scope.
- **PARTIALLY SUPPORTED:** true only for some comparators, domains or conditions, or only descriptively. It must be
  stated with its restriction.
- **NOT SUPPORTED:** contradicted, not demonstrated, or not testable as stated.

Stage-2 primary evidence is the confirmation partition of VALIDATED evidence models (IAM-02/03/04/06). Numbers are from
`RESULTS.md` and `results/stage2/tables/`. Partially supported claims must not be restated as supported.

| ID | Claim | Verdict | Evidence and required qualification |
|---|---|---|---|
| C1 | AVOI reduces evidence acquisition compared with fixed/exhaustive strategies. | SUPPORTED | Stage 1: all three datasets. Stage 2, VALIDATED IAM: −4.55 acquisitions vs All Evidence and −3.16 vs Checklist (Holm p < 1e-128; S3 supported). Not testable for AIT/CERT in Stage 2 (no eligible model). Qualification: on IAM the gain comes from value-based stopping over a fixed per-objective source order, not from adaptive source selection. |
| C2 | AVOI reduces acquisition cost. | PARTIALLY SUPPORTED | Lower cost than All Evidence (−0.58), Checklist (−0.17), Information Gain (−0.09), Cheapest First, Confidence Threshold and Random. **Higher** than Lookahead-2 (+0.13), Myopic VOI (+0.15) and Generic VOI (+0.41). |
| C3 | AVOI has lower UAR than generic symmetric VOI. | SUPPORTED | Stage 1: all three datasets. Stage 2, VALIDATED IAM: 0.003 vs 0.268 (difference −0.265 [−0.315, −0.219]; McNemar Holm p = 2.4e-22). Qualification: part of the gap comes from AVOI's HumanReview option (coverage 0.68 vs 1.00). |
| C4 | AVOI has lower UAR than information gain. | NOT SUPPORTED | Stage-1 H2 not supported. Stage 2, VALIDATED IAM: identical UAR (0.003 vs 0.003; McNemar p = 1). Information gain has numerically lower loss and higher coverage. The adequacy gate does not change this. |
| C5 | AVOI has lower expected loss than all-evidence. | NOT SUPPORTED | Stage 1 (IAM): All Evidence lower (0.316 vs 0.381). Stage 2, VALIDATED IAM: AVOI higher by +0.042 [0.005, 0.082]. All Evidence achieves this with 4.1× the acquisitions. |
| C6 | AVOI has a better risk-coverage trade-off than confidence threshold. | PARTIALLY SUPPORTED | Stage 2, VALIDATED IAM: normalised UAR–coverage AURC 0.0023 vs 0.0974. Stage 1: IAM and CERT. Descriptive only (no pre-specified test), and demonstrated on one eligible domain in Stage 2. |
| C7 | Asymmetric assurance loss changes unsafe-assurance behavior. | SUPPORTED | Identical symmetric-loss AVOI vs 10:2:1 AVOI, VALIDATED IAM: UAR −0.021 [−0.039, −0.004], FAA −0.023 [−0.044, −0.005], more acquisitions (+0.62), higher coverage (+0.076). Qualification: paired McNemar on discordant unsafe assurances is 1 vs 7 (p = 0.070), so the effect size is uncertain. On AIT (raw): 0 vs 6 (p = 0.031). |
| C8 | AVOI remains effective under missing evidence. | PARTIALLY SUPPORTED | IAM: coverage is stable (0.78–0.83) and acquisitions drop, but UAR rises with partial pre-revealed evidence (MCAR 80%: 0.031 vs 0.013 at cold start) and is not uniformly better than Information Gain or Checklist. Not assessable autonomously on AIT/CERT. |
| C9 | AVOI reduces privacy exposure when privacy burden is weighted. | PARTIALLY SUPPORTED | IAM: exposure 0.282 → 0.113 as μ goes 0.25 → 1.0, but expected loss rises 0.389 → 0.694 and coverage falls 0.76 → 0.50. There is no reduction for μ ≤ 0.25. Privacy exposure is a proxy, not a legal risk measure. |
| C10 | Evidence-model adequacy is necessary for trustworthy AVOI value estimates. | PARTIALLY SUPPORTED | Inadequate models give untrustworthy estimates: CERT realised-minus-predicted loss +2.28 and AIT-EXFIL +0.97 even with all evidence; AIT-EXFIL discrimination is inverted. But two IAM models RESTRICTED only by the slope rule had small gaps (+0.05, +0.01) and reasonable raw behaviour. "Necessary" is not established, and the adequacy condition was motivated post hoc by Stage 1. |
| C11 | The adequacy gate prevents autonomous use in unsupported domains. | SUPPORTED | S2 supported: 0 autonomous decisions for all five non-validated models; correct `MODEL_ADEQUACY_*` reasons; VALIDATED models unaffected; never converted to NotAssured. Qualification: this is a restriction, not an acquisition improvement (S4: coverage losses of 0.98–1.00 wherever UAR fell). |
| C12 | AVOI generalizes across all datasets. | NOT SUPPORTED | Stage 2: no AIT or CERT evidence model is eligible (AIT-EXFIL UNSUPPORTED; AIT-INTRUSION and CERT RESTRICTED). Stage-1 AIT UAR was ≈ 0.31 for every method. |
| C13 | AVOI is safer than all strong baselines. | NOT SUPPORTED | UAR ties Information Gain and Lookahead-2. Expected loss is higher than All Evidence and not lower than Information Gain. |
| C14 | AVOI is more efficient at matched non-degenerate safety/coverage. | NOT SUPPORTED | The frozen joint criterion (UAR ≤ η AND coverage ≥ γ) remained degenerate: all 48 AVOI points achieved on validation (and all 48 for Information Gain, Checklist, Cheapest First, Lookahead-2 and Random) had zero correct assurances. AVOI achieved only 3 of 16 coverage-matched targets. Not demonstrated. |
| C15 | AVOI should replace human assurance review. | NOT SUPPORTED | Nothing tests this. Escalation and gating are integral. Eligibility holds for 4 of 9 models, all in a synthetic testbed. |

## Statements that must not appear

- "AVOI outperformed all baselines" (in any unqualified form).
- "AVOI is safer than information gain" or "AVOI beats all-evidence".
- "The adequacy gate improves AVOI's acquisition policy" or "the gate makes H2 supported".
- "The adequacy policy was pre-registered". It was defined for Stage 2 after Stage-1 results were known.
- "Passing the adequacy gate demonstrates regulatory compliance". Labels are objective predicates or attack activity,
  not compliance labels.
- "AVOI generalizes to AIT/CERT" or "is ready for autonomous use outside validated models".
