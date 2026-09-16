**Stage 3 WP2. External-domain (AIT, CERT) evidence-model adequacy (unchanged Stage-2 policy)**

| domain | objective | model | alpha | development_datasets | target_adaptation | calibrator | adequacy_validation_N | violations | independent_groups | AUROC | AUPRC | PR_skill | Brier | BSS | ECE | calibration_slope | adequacy_status | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ait | AIT-EXFIL | hgb | n/a | russellmitchell, santos, fox, harrison, wardbeck | target-calibrated (primary) | isotonic | 504 | 0 | 84 | n/a | n/a | n/a | 0.000 | 1.000 [nan, nan] | 0.002 [nan, nan] | n/a | RESTRICTED | INSUFFICIENT_ADEQUACY_SAMPLE_SUPPORT |
| ait | AIT-INTRUSION | tan | 2.000 | russellmitchell, santos, fox, harrison, wardbeck | target-calibrated (primary) | none | 504 | 6 | 84 | 0.994 [0.983, 1.000] | 0.707 [0.239, 1.000] | 0.704 [0.235, 1.000] | 0.008 | 0.351 [0.105, 0.569] | 0.007 [0.003, 0.021] | 1.637 [1.179, 94.817] | RESTRICTED | INSUFFICIENT_ADEQUACY_SAMPLE_SUPPORT |
| cert | CERT-INSIDER | tan | 5.000 | r4.2, r5.2 | target-calibrated (primary) | sigmoid | 394 | 21 | 187 | 0.895 [0.671, 0.953] | 0.306 [0.029, 0.600] | 0.267 [0.017, 0.560] | 0.043 | 0.744 [0.554, 0.918] | 0.017 [0.005, 0.064] | 1.310 [0.476, 2.066] | VALIDATED | ALL_PRIMARY_ADEQUACY_CONDITIONS_MET |
