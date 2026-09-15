**Stage 2. Zero-acquisition episodes and acquisition-required subset**

| domain | method | P(N_acq=0) | P(N_acq>0) | E[N_acq] | E[N_acq | N_acq>0] | validated_model_episodes | acquisition_required_share_validated | acq_required_UAR | acq_required_coverage | acq_required_expected_loss | acq_required_mean_acquisitions |
|---|---|---|---|---|---|---|---|---|---|---|---|
| iam | All Evidence | 0.000 | 1.000 | 6.167 | 6.167 | 768 | 1.000 | 0.000 | 0.771 | 0.398 | 6.000 |
| iam | Checklist | 0.000 | 1.000 | 4.443 | 4.443 | 768 | 1.000 | 0.010 | 0.733 | 0.452 | 4.612 |
| iam | Cheapest First | 0.000 | 1.000 | 5.023 | 5.023 | 768 | 1.000 | 0.007 | 0.671 | 0.434 | 5.263 |
| iam | Information Gain | 0.000 | 1.000 | 2.465 | 2.465 | 768 | 1.000 | 0.003 | 0.738 | 0.423 | 2.531 |
| iam | Generic VOI | 0.167 | 0.833 | 1.161 | 1.393 | 768 | 0.750 | 0.062 | 1.000 | 0.424 | 1.280 |
| iam | Confidence Threshold | 0.000 | 1.000 | 4.581 | 4.581 | 768 | 1.000 | 0.014 | 0.634 | 0.467 | 4.811 |
| iam | Myopic Cost-Sensitive VOI | 0.333 | 0.667 | 0.933 | 1.400 | 768 | 1.000 | 0.007 | 1.000 | 0.578 | 1.150 |
| iam | Lookahead-2 | 0.000 | 1.000 | 1.869 | 1.869 | 768 | 1.000 | 0.003 | 0.659 | 0.430 | 1.591 |
| iam | AVOI | 0.000 | 1.000 | 1.481 | 1.481 | 768 | 1.000 | 0.003 | 0.677 | 0.440 | 1.454 |
| ait | All Evidence | 0.000 | 1.000 | 10.000 | 10.000 | 0 | n/a | n/a | n/a | n/a | n/a |
| ait | Checklist | 1.000 | 0.000 | 0.000 | n/a | 0 | n/a | n/a | n/a | n/a | n/a |
| ait | Cheapest First | 1.000 | 0.000 | 0.000 | n/a | 0 | n/a | n/a | n/a | n/a | n/a |
| ait | Information Gain | 1.000 | 0.000 | 0.000 | n/a | 0 | n/a | n/a | n/a | n/a | n/a |
| ait | Generic VOI | 1.000 | 0.000 | 0.000 | n/a | 0 | n/a | n/a | n/a | n/a | n/a |
| ait | Confidence Threshold | 1.000 | 0.000 | 0.000 | n/a | 0 | n/a | n/a | n/a | n/a | n/a |
| ait | Myopic Cost-Sensitive VOI | 0.500 | 0.500 | 3.492 | 6.985 | 0 | n/a | n/a | n/a | n/a | n/a |
| ait | Lookahead-2 | 0.500 | 0.500 | 0.556 | 1.113 | 0 | n/a | n/a | n/a | n/a | n/a |
| ait | AVOI | 0.500 | 0.500 | 0.555 | 1.109 | 0 | n/a | n/a | n/a | n/a | n/a |
| cert | All Evidence | 0.000 | 1.000 | 10.000 | 10.000 | 0 | n/a | n/a | n/a | n/a | n/a |
| cert | Checklist | 0.000 | 1.000 | 10.000 | 10.000 | 0 | n/a | n/a | n/a | n/a | n/a |
| cert | Cheapest First | 0.000 | 1.000 | 10.000 | 10.000 | 0 | n/a | n/a | n/a | n/a | n/a |
| cert | Information Gain | 0.000 | 1.000 | 7.118 | 7.118 | 0 | n/a | n/a | n/a | n/a | n/a |
| cert | Generic VOI | 0.000 | 1.000 | 1.834 | 1.834 | 0 | n/a | n/a | n/a | n/a | n/a |
| cert | Confidence Threshold | 0.000 | 1.000 | 10.000 | 10.000 | 0 | n/a | n/a | n/a | n/a | n/a |
| cert | Myopic Cost-Sensitive VOI | 0.000 | 1.000 | 2.244 | 2.244 | 0 | n/a | n/a | n/a | n/a | n/a |
| cert | Lookahead-2 | 0.000 | 1.000 | 4.218 | 4.218 | 0 | n/a | n/a | n/a | n/a | n/a |
| cert | AVOI | 0.000 | 1.000 | 3.036 | 3.036 | 0 | n/a | n/a | n/a | n/a | n/a |
