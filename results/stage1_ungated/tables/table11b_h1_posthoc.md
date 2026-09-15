**Table 11b. POST-HOC (deviation D1): H1 with non-degenerate safety matching**

| dataset | target | n_pairs | mean_acq_AVOI | mean_acq_B1 | acq_diff | acq_ci_low | acq_ci_high | wilcoxon_p | rank_biserial | uar_diff | uar_ci_low | uar_ci_high | p_holm | verdict_posthoc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| iam | 0.010 | 1728 | 1.060 | 3.112 | -2.053 | -2.134 | -1.975 | 0.000 | -0.999 | 0.000 | -0.004 | 0.004 | 0.000 | supported |
| iam | 0.020 | 1920 | 0.971 | 3.276 | -2.305 | -2.388 | -2.224 | 0.000 | -1.000 | -0.003 | -0.008 | 0.003 | 0.000 | supported |
| iam | 0.050 | 1920 | 0.970 | 3.154 | -2.184 | -2.262 | -2.107 | 0.000 | -1.000 | -0.015 | -0.024 | -0.007 | 0.000 | supported |
| ait | 0.010 | 2304 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | not testable - still degenerate (both methods acquire no evidence at the selected thresholds) |
| ait | 0.020 | 2304 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | not testable - still degenerate (both methods acquire no evidence at the selected thresholds) |
| ait | 0.050 | 2304 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | not testable - still degenerate (both methods acquire no evidence at the selected thresholds) |
| cert | 0.010 | 214 | 1.537 | 6.780 | -5.243 | -5.565 | -4.916 | 0.000 | -1.000 | 0.000 | 0.000 | 0.000 | 0.000 | supported |
| cert | 0.020 | 214 | 1.537 | 6.603 | -5.065 | -5.383 | -4.748 | 0.000 | -1.000 | 0.000 | 0.000 | 0.000 | 0.000 | supported |
| cert | 0.050 | 969 | 1.251 | 3.424 | -2.173 | -2.259 | -2.094 | 0.000 | -0.995 | -0.012 | -0.025 | -0.003 | 0.000 | supported |
