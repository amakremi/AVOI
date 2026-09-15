**Stage-2 hypotheses S1-S4**

| hypothesis | verdict | details | domain |
|---|---|---|---|
| S1 | supported | non-validated models: ['iam|IAM-01-MFA-PRIV', 'iam|IAM-05-BREAKGLASS', 'ait|AIT-EXFIL', 'ait|AIT-INTRUSION', 'cert|CERT-INSIDER']; UAR: non-validated 0.0097 vs validated 0.0035, difference CI [-0.0041, 0.0170] | expected_loss: non-validated 0.6050 vs validated 0.4401, difference CI [0.1131, 0.2201] | n/a |
| S2 | supported | autonomous decisions for non-validated models: 0; correct gate reasons: True; validated models unaffected: True | n/a |
| S3 | supported | AVOI vs All Evidence: diff -4.546 [-4.572, -4.518], Holm p=3.7e-134; AVOI vs Checklist: diff -3.158 [-3.251, -3.062], Holm p=3.22e-130 | context (not part of the rule): AVOI vs All Evidence expected_loss diff +0.0417 [+0.0052, +0.0820]; AVOI vs All Evidence UAR diff +0.0035 [+0.0000, +0.0107]; AVOI vs Checklist expected_loss diff -0.0117 [-0.0586, +0.0286]; AVOI vs Checklist UAR diff -0.0070 [-0.0177, +0.0000] | Controlled IAM |
| S3 | not testable (no VALIDATED model) |  | AIT-LDS v2.0 |
| S3 | not testable (no VALIDATED model) |  | CERT (r4.2 dev / r5.2 confirmation) |
| S4 | supported | iam|IAM-01-MFA-PRIV: dUAR -0.0169 [-0.0612, +0.0000], dCoverage -1.0000 [-1.0000, -1.0000] | iam|IAM-05-BREAKGLASS: dUAR -0.0385 [-0.0714, -0.0098], dCoverage -1.0000 [-1.0000, -1.0000] | ait|AIT-EXFIL: dUAR +0.0000 [+0.0000, +0.0000], dCoverage +0.0000 [+0.0000, +0.0000] | ait|AIT-INTRUSION: dUAR -0.6000 [-1.0000, -0.1667], dCoverage -0.9826 [-0.9910, -0.9722] | cert|CERT-INSIDER: dUAR +0.0000 [+0.0000, +0.0000], dCoverage +0.0000 [+0.0000, +0.0000] | n/a |
