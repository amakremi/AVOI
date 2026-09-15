# Model uncertainty vs decision uncertainty (Stage 2)

*Decision uncertainty*: the evidence model is VALIDATED but the acquired evidence leaves the Bayes risk above the
threshold, or no remaining action has positive assurance value -> AVOI acquires more evidence or escalates
(stop reasons `no_positive_value`, `exhausted`, `budget`).

*Model inadequacy*: the evidence model failed discrimination, calibration or sample-support conditions on the
adequacy-validation partition -> autonomous AVOI is withheld for the whole model (reason `MODEL_ADEQUACY_RESTRICTED`
or `MODEL_ADEQUACY_UNSUPPORTED`). More evidence is not assumed to repair this, and it is never converted to NotAssured.

Counts on the confirmation partition (AVOI, cold start, validation-tuned threshold):

| domain | objective | adequacy status | escalation type | escalations | Y=0 | Y=1 | false assurances prevented | false non-assurances prevented | correct autonomous decisions withheld | coverage lost |
|---|---|---|---|---|---|---|---|---|---|---|
| iam | IAM-01-MFA-PRIV | RESTRICTED | evidence-uncertainty escalation (raw AVOI) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 |
| iam | IAM-01-MFA-PRIV | RESTRICTED | model-adequacy escalation (gate) | 192 | 59 | 133 | 1 | 23 | 168 | 1.000 |
| iam | IAM-02-TERM-DISABLED | VALIDATED | evidence-uncertainty escalation (raw AVOI) | 36 | 3 | 33 | 0 | 33 | 3 | 0.188 |
| iam | IAM-02-TERM-DISABLED | VALIDATED | model-adequacy escalation (gate) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 |
| iam | IAM-03-PRIV-AUTHZ | VALIDATED | evidence-uncertainty escalation (raw AVOI) | 111 | 41 | 70 | 0 | 70 | 41 | 0.578 |
| iam | IAM-03-PRIV-AUTHZ | VALIDATED | model-adequacy escalation (gate) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 |
| iam | IAM-04-DORMANT | VALIDATED | evidence-uncertainty escalation (raw AVOI) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 |
| iam | IAM-04-DORMANT | VALIDATED | model-adequacy escalation (gate) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 |
| iam | IAM-05-BREAKGLASS | RESTRICTED | evidence-uncertainty escalation (raw AVOI) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 |
| iam | IAM-05-BREAKGLASS | RESTRICTED | model-adequacy escalation (gate) | 192 | 104 | 88 | 4 | 10 | 178 | 1.000 |
| iam | IAM-06-ACCESS-REVIEW | VALIDATED | evidence-uncertainty escalation (raw AVOI) | 101 | 46 | 55 | 0 | 55 | 46 | 0.526 |
| iam | IAM-06-ACCESS-REVIEW | VALIDATED | model-adequacy escalation (gate) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 |
| ait | AIT-EXFIL | UNSUPPORTED | evidence-uncertainty escalation (raw AVOI) | 1440 | 910 | 530 | 0 | 530 | 910 | 1.000 |
| ait | AIT-EXFIL | UNSUPPORTED | model-adequacy escalation (gate) | 1440 | 0 | 0 | 0 | 0 | 0 | 0.000 |
| ait | AIT-INTRUSION | RESTRICTED | evidence-uncertainty escalation (raw AVOI) | 25 | 6 | 19 | 6 | 0 | 19 | 0.017 |
| ait | AIT-INTRUSION | RESTRICTED | model-adequacy escalation (gate) | 1440 | 9 | 1406 | 9 | 0 | 1406 | 0.983 |
| cert | CERT-INSIDER | RESTRICTED | evidence-uncertainty escalation (raw AVOI) | 769 | 351 | 418 | 157 | 106 | 506 | 1.000 |
| cert | CERT-INSIDER | RESTRICTED | model-adequacy escalation (gate) | 769 | 0 | 0 | 0 | 0 | 0 | 0.000 |

For model-adequacy escalations, 'escalations' counts gated episodes; the prevented/withheld counts refer to episodes whose
raw AVOI decision was autonomous (episodes already escalated for evidence uncertainty are not double-counted).

## A. Can high initial uncertainty be resolved by acquisition? (raw AVOI, confirmation)

High initial uncertainty = acquisition-required episodes (initial evidence insufficient for autonomous termination at the
validation-tuned threshold; predefined). 'Resolved' = AVOI terminates autonomously after acquiring evidence.

| domain | objective | status | acquisition-required episodes | mean initial Bayes risk | resolved autonomously | error among resolved | mean acquisitions | realized loss |
|---|---|---|---|---|---|---|---|---|
| ait | AIT-EXFIL | UNSUPPORTED | 1440 | 0.569 | 0.000 | nan | 0.00 | 1.000 |
| ait | AIT-INTRUSION | RESTRICTED | 1440 | 0.176 | 0.983 | 0.006 | 1.11 | 0.080 |
| cert | CERT-INSIDER | RESTRICTED | 769 | 1.000 | 0.000 | nan | 3.04 | 1.000 |
| iam | IAM-01-MFA-PRIV | RESTRICTED | 192 | 1.000 | 1.000 | 0.125 | 1.00 | 0.292 |
| iam | IAM-02-TERM-DISABLED | VALIDATED | 192 | 1.000 | 0.812 | 0.000 | 1.00 | 0.188 |
| iam | IAM-03-PRIV-AUTHZ | VALIDATED | 192 | 1.000 | 0.422 | 0.198 | 2.49 | 0.745 |
| iam | IAM-04-DORMANT | VALIDATED | 192 | 1.000 | 1.000 | 0.125 | 1.00 | 0.250 |
| iam | IAM-05-BREAKGLASS | RESTRICTED | 192 | 0.859 | 1.000 | 0.073 | 2.07 | 0.312 |
| iam | IAM-06-ACCESS-REVIEW | VALIDATED | 192 | 0.706 | 0.474 | 0.011 | 1.33 | 0.578 |

## B. Is inadequacy a model-level property that more evidence does not repair?

Predicted vs realized loss of autonomous decisions: predicted = expected loss of the chosen decision under the model's
own (calibrated) posterior; realized = loss against confirmation labels. A trustworthy model has a small gap; the gap is
shown for AVOI and for All Evidence (every source acquired).

| domain | objective | status | method | autonomous decisions | predicted loss | realized loss | realized - predicted | autonomous error rate |
|---|---|---|---|---|---|---|---|---|
| ait | AIT-EXFIL | UNSUPPORTED | All Evidence | 746 | 0.456 | 1.421 | +0.965 | 0.710 |
| ait | AIT-INTRUSION | RESTRICTED | AVOI | 1415 | 0.115 | 0.064 | -0.052 | 0.006 |
| ait | AIT-INTRUSION | RESTRICTED | All Evidence | 1437 | 0.089 | 0.104 | +0.015 | 0.010 |
| cert | CERT-INSIDER | RESTRICTED | All Evidence | 674 | 0.213 | 2.493 | +2.279 | 0.315 |
| iam | IAM-01-MFA-PRIV | RESTRICTED | AVOI | 192 | 0.183 | 0.292 | +0.109 | 0.125 |
| iam | IAM-01-MFA-PRIV | RESTRICTED | All Evidence | 189 | 0.097 | 0.148 | +0.052 | 0.032 |
| iam | IAM-02-TERM-DISABLED | VALIDATED | AVOI | 156 | 0.085 | 0.000 | -0.085 | 0.000 |
| iam | IAM-02-TERM-DISABLED | VALIDATED | All Evidence | 166 | 0.076 | 0.036 | -0.040 | 0.018 |
| iam | IAM-03-PRIV-AUTHZ | VALIDATED | AVOI | 81 | 0.660 | 0.395 | -0.265 | 0.198 |
| iam | IAM-03-PRIV-AUTHZ | VALIDATED | All Evidence | 78 | 0.403 | 0.256 | -0.147 | 0.128 |
| iam | IAM-04-DORMANT | VALIDATED | AVOI | 192 | 0.193 | 0.250 | +0.057 | 0.125 |
| iam | IAM-04-DORMANT | VALIDATED | All Evidence | 185 | 0.157 | 0.173 | +0.016 | 0.086 |
| iam | IAM-05-BREAKGLASS | RESTRICTED | AVOI | 192 | 0.293 | 0.312 | +0.019 | 0.073 |
| iam | IAM-05-BREAKGLASS | RESTRICTED | All Evidence | 189 | 0.285 | 0.296 | +0.011 | 0.063 |
| iam | IAM-06-ACCESS-REVIEW | VALIDATED | AVOI | 91 | 0.000 | 0.110 | +0.110 | 0.011 |
| iam | IAM-06-ACCESS-REVIEW | VALIDATED | All Evidence | 163 | 0.293 | 0.442 | +0.149 | 0.221 |

Interpretation rule (fixed before inspection): episode-level uncertainty is resolvable when acquisition-required episodes
of VALIDATED models terminate autonomously with low error; model inadequacy is indicated when the realized-minus-predicted
gap stays large even with all evidence acquired.
