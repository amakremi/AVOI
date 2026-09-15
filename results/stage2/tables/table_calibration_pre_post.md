**Stage 2 (supplementary). Calibration before/after the development-selected calibrator**

| domain | objective | calibrator | calibrator_cv_log_loss | dev_oof_ECE_before | dev_oof_ECE_after | dev_oof_slope_before | dev_oof_slope_after | validation_ECE_uncalibrated | validation_ECE_calibrated | validation_BSS_uncalibrated | validation_BSS_calibrated | validation_slope_uncalibrated | validation_slope_calibrated | validation_AUROC_uncalibrated | validation_AUROC_calibrated | masked_state_ECE_calibrated | masked_state_AUROC_calibrated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ait | AIT-EXFIL | sigmoid | {"none": 1.3226, "sigmoid": 0.7091, "isotonic": 5.4667, "beta": 1.8548} | 0.511 | 0.049 | -0.425 | 0.925 | 0.203 | 0.587 | 0.596 | -0.451 | 3.009 | -6.548 | 0.976 | 0.024 | 0.412 | 0.171 |
| ait | AIT-INTRUSION | sigmoid | {"none": 0.06, "sigmoid": 0.0597, "isotonic": 0.1002, "beta": 0.0847} | 0.007 | 0.005 | 0.409 | 1.001 | 0.016 | 0.003 | -0.335 | -0.002 | 0.259 | 0.634 | 0.686 | 0.686 | 0.001 | 0.589 |
| cert | CERT-INSIDER | none | {"none": 0.4072, "sigmoid": 0.4137, "isotonic": 0.4403, "beta": 0.4175} | 0.035 | 0.035 | 0.747 | 0.747 | 0.183 | 0.183 | 0.080 | 0.080 | 0.283 | 0.283 | 0.764 | 0.764 | 0.135 | 0.709 |
| iam | IAM-01-MFA-PRIV | beta | {"none": 0.1842, "sigmoid": 0.183, "isotonic": 0.2125, "beta": 0.1825} | 0.024 | 0.022 | 1.455 | 1.184 | 0.061 | 0.048 | 0.871 | 0.888 | 2.362 | 1.701 | 0.999 | 0.999 | 0.058 | 0.919 |
| iam | IAM-02-TERM-DISABLED | none | {"none": 0.2343, "sigmoid": 0.2368, "isotonic": 0.2629, "beta": 0.2379} | 0.012 | 0.012 | 1.128 | 1.128 | 0.024 | 0.024 | 0.937 | 0.937 | 1.324 | 1.324 | 0.998 | 0.998 | 0.042 | 0.916 |
| iam | IAM-03-PRIV-AUTHZ | none | {"none": 0.53, "sigmoid": 0.5333, "isotonic": 0.5412, "beta": 0.5346} | 0.056 | 0.056 | 0.905 | 0.905 | 0.089 | 0.089 | 0.316 | 0.316 | 1.208 | 1.208 | 0.832 | 0.832 | 0.058 | 0.738 |
| iam | IAM-04-DORMANT | none | {"none": 0.3515, "sigmoid": 0.3635, "isotonic": 0.4198, "beta": 0.3614} | 0.015 | 0.015 | 1.455 | 1.455 | 0.018 | 0.018 | 0.779 | 0.779 | 1.197 | 1.197 | 0.952 | 0.952 | 0.057 | 0.813 |
| iam | IAM-05-BREAKGLASS | beta | {"none": 0.4302, "sigmoid": 0.4301, "isotonic": 0.4534, "beta": 0.4277} | 0.069 | 0.054 | 1.305 | 1.149 | 0.061 | 0.055 | 0.844 | 0.850 | 5.129 | 4.648 | 0.993 | 0.993 | 0.090 | 0.856 |
| iam | IAM-06-ACCESS-REVIEW | isotonic | {"none": 0.4878, "sigmoid": 0.4906, "isotonic": 0.4847, "beta": 0.4904} | 0.097 | 0.028 | 0.948 | 0.698 | 0.089 | 0.049 | 0.560 | 0.598 | 1.239 | 1.264 | 0.938 | 0.940 | 0.039 | 0.801 |
