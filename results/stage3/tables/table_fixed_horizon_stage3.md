**Stage 3 WP1. Adaptive vs Frozen-Order AVOI, fixed evidence horizons k=2,3**

| objective | horizon_k | adaptive_loss | frozen_loss | difference | ci_low | ci_high | n_pairs | signflip_p | adaptive_lower | signflip_p_holm |
|---|---|---|---|---|---|---|---|---|---|---|
| IAM-01-MFA-PRIV | 2 | 0.180 | 0.180 | 0.000 | 0.000 | 0.000 | 256 | 1.000 | 0 | 1.000 |
| IAM-01-MFA-PRIV | 3 | 0.164 | 0.164 | 0.000 | 0.000 | 0.000 | 256 | 1.000 | 0 | 1.000 |
| IAM-02-TERM-DISABLED | 2 | 0.156 | 0.242 | -0.086 | -0.121 | -0.055 | 256 | 0.000 | 1 | 0.001 |
| IAM-02-TERM-DISABLED | 3 | 0.129 | 0.242 | -0.113 | -0.156 | -0.074 | 256 | 0.000 | 1 | 0.001 |
| IAM-03-PRIV-AUTHZ | 2 | 0.453 | 0.434 | 0.020 | -0.043 | 0.109 | 256 | 0.913 | 0 | 1.000 |
| IAM-03-PRIV-AUTHZ | 3 | 0.520 | 0.398 | 0.121 | 0.016 | 0.242 | 256 | 0.025 | 0 | 0.098 |
