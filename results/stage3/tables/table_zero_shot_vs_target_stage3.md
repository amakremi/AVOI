**Stage 3 WP2. Zero-shot vs target-calibrated external evidence models**

| domain | objective | variant | AUROC | PR_skill | BSS | ECE | calibration_slope | n_violated | n_satisfied |
|---|---|---|---|---|---|---|---|---|---|
| ait | AIT-EXFIL | zero_shot | n/a | n/a | 0.844 [nan, nan] | 0.168 [nan, nan] | n/a | 0 | 504 |
| ait | AIT-EXFIL | target_calibrated | n/a | n/a | 1.000 [nan, nan] | 0.002 [nan, nan] | n/a | 0 | 504 |
| ait | AIT-INTRUSION | zero_shot | 0.994 [0.983, 1.000] | 0.704 [0.235, 1.000] | 0.351 [0.105, 0.569] | 0.007 [0.003, 0.021] | 1.637 [1.179, 94.817] | 6 | 498 |
| ait | AIT-INTRUSION | target_calibrated | 0.994 [0.983, 1.000] | 0.704 [0.235, 1.000] | 0.351 [0.105, 0.569] | 0.007 [0.003, 0.021] | 1.637 [1.179, 94.817] | 6 | 498 |
| cert | CERT-INSIDER | zero_shot | 0.895 [0.671, 0.953] | 0.267 [0.017, 0.560] | 0.488 [0.350, 0.618] | 0.113 [0.083, 0.146] | 0.743 [0.270, 1.172] | 21 | 373 |
| cert | CERT-INSIDER | target_calibrated | 0.895 [0.671, 0.953] | 0.267 [0.017, 0.560] | 0.744 [0.554, 0.918] | 0.017 [0.005, 0.064] | 1.310 [0.476, 2.066] | 21 | 373 |
