**Stage 2. Evidence-uncertainty vs model-adequacy escalation (AVOI)**

| domain | objective | adequacy_status | type | escalations | Y0 | Y1 | false_assurances_prevented | false_non_assurances_prevented | correct_autonomous_withheld | coverage_lost | decisions_changed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| iam | IAM-01-MFA-PRIV | RESTRICTED | evidence-uncertainty escalation (raw AVOI) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 |
| iam | IAM-01-MFA-PRIV | RESTRICTED | model-adequacy escalation (gate) | 192 | 59 | 133 | 1 | 23 | 168 | 1.000 | 192 |
| iam | IAM-02-TERM-DISABLED | VALIDATED | evidence-uncertainty escalation (raw AVOI) | 36 | 3 | 33 | 0 | 33 | 3 | 0.188 | 36 |
| iam | IAM-02-TERM-DISABLED | VALIDATED | model-adequacy escalation (gate) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 |
| iam | IAM-03-PRIV-AUTHZ | VALIDATED | evidence-uncertainty escalation (raw AVOI) | 111 | 41 | 70 | 0 | 70 | 41 | 0.578 | 111 |
| iam | IAM-03-PRIV-AUTHZ | VALIDATED | model-adequacy escalation (gate) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 |
| iam | IAM-04-DORMANT | VALIDATED | evidence-uncertainty escalation (raw AVOI) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 |
| iam | IAM-04-DORMANT | VALIDATED | model-adequacy escalation (gate) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 |
| iam | IAM-05-BREAKGLASS | RESTRICTED | evidence-uncertainty escalation (raw AVOI) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 |
| iam | IAM-05-BREAKGLASS | RESTRICTED | model-adequacy escalation (gate) | 192 | 104 | 88 | 4 | 10 | 178 | 1.000 | 192 |
| iam | IAM-06-ACCESS-REVIEW | VALIDATED | evidence-uncertainty escalation (raw AVOI) | 101 | 46 | 55 | 0 | 55 | 46 | 0.526 | 101 |
| iam | IAM-06-ACCESS-REVIEW | VALIDATED | model-adequacy escalation (gate) | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 |
| ait | AIT-EXFIL | UNSUPPORTED | evidence-uncertainty escalation (raw AVOI) | 1440 | 910 | 530 | 0 | 530 | 910 | 1.000 | 1440 |
| ait | AIT-EXFIL | UNSUPPORTED | model-adequacy escalation (gate) | 1440 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 |
| ait | AIT-INTRUSION | RESTRICTED | evidence-uncertainty escalation (raw AVOI) | 25 | 6 | 19 | 6 | 0 | 19 | 0.017 | 25 |
| ait | AIT-INTRUSION | RESTRICTED | model-adequacy escalation (gate) | 1440 | 9 | 1406 | 9 | 0 | 1406 | 0.983 | 1415 |
| cert | CERT-INSIDER | RESTRICTED | evidence-uncertainty escalation (raw AVOI) | 769 | 351 | 418 | 157 | 106 | 506 | 1.000 | 769 |
| cert | CERT-INSIDER | RESTRICTED | model-adequacy escalation (gate) | 769 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 |
