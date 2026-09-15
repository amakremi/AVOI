> Stage 1 (original ungated experiment). Manuscript-facing copy: the method display name is AVOI (the historical label is retained only in the archived files); all numbers identical to the archived artefact.

# AVOI — experimental results (auto-generated)

Frozen configuration SHA-256: `4370311ede64cd3215fc4bc3ceeddbbbcef4a66453697b0595d80f1bca7715c8` (frozen 2026-09-14T11:55:42+00:00).
All numbers are computed from `results/raw` by `experiments/run_statistics.py`. Held-out episodes only; 95% CIs are stratified bootstrap percentile intervals (5,000 resamples). Layer A = controlled IAM testbed (objective-level ground truth); Layer B = public replay micro-claims (AIT-LDS v2.0, CERT r4.2) — NOT compliance decisions.

## Datasets and episodes

- Controlled IAM testbed (Layer A): IAM-01-MFA-PRIV: 320 episodes (86 violated/refuted), 7 actions; IAM-02-TERM-DISABLED: 320 episodes (81 violated/refuted), 6 actions; IAM-03-PRIV-AUTHZ: 320 episodes (101 violated/refuted), 7 actions; IAM-04-DORMANT: 320 episodes (116 violated/refuted), 5 actions; IAM-05-BREAKGLASS: 320 episodes (167 violated/refuted), 6 actions; IAM-06-ACCESS-REVIEW: 320 episodes (190 violated/refuted), 6 actions
- AIT-LDS v2.0 replay (Layer B): AIT-EXFIL: 1152 episodes (848 violated/refuted), 10 actions; AIT-INTRUSION: 1152 episodes (12 violated/refuted), 10 actions
- CERT r4.2 replay (Layer B): CERT-INSIDER: 969 episodes (326 violated/refuted), 10 actions
- Excluded: Splunk BOTS v3 (answer key e-mail gated; proprietary index format), LANL cyber1 (e-mail form gated).

## RQ1 — Acquisition efficiency

**Controlled IAM testbed (Layer A)** — AVOI: mean acquisitions 1.638 [1.596, 1.680], normalised cost 0.6975 [0.6754, 0.7192], expected loss 0.3807.
- Paired difference in acquisitions (AVOI − baseline):
  - vs B0-AllEvidence: difference -4.5286 [95% CI -4.5724, -4.4844], wilcoxon p=0, Holm p=0 (statistically significant)
  - vs B1-FixedChecklist: difference -2.8797 [95% CI -2.9443, -2.8161], wilcoxon p=0, Holm p=0 (statistically significant)
  - vs B2-Random: difference -2.1841 [95% CI -2.2370, -2.1319], wilcoxon p=0, Holm p=0 (statistically significant)
  - vs B3-CheapestFirst: difference -3.3714 [95% CI -3.4370, -3.3057], wilcoxon p=9.67e-310, Holm p=4.84e-309 (statistically significant)
  - vs B4-InformationGain: difference -0.6302 [95% CI -0.6885, -0.5745], wilcoxon p=6.37e-89, Holm p=1.91e-88 (statistically significant)
  - vs B5-GenericVOI: difference +0.6854 [95% CI +0.6333, +0.7375], wilcoxon p=5.91e-106, Holm p=2.37e-105 (statistically significant)
  - vs B6-ConfidenceThreshold: difference -3.0917 [95% CI -3.1578, -3.0255], wilcoxon p=0, Holm p=0 (statistically significant)
  - vs B7-MyopicCostSensitiveVOI: difference +0.5625 [95% CI +0.4948, +0.6302], wilcoxon p=2.89e-49, Holm p=5.79e-49 (statistically significant)
  - vs B7b-Lookahead2VOI: difference -0.2406 [95% CI -0.2781, -0.2036], wilcoxon p=8.8e-35, Holm p=8.8e-35 (statistically significant)
- Paired difference in normalised cost (AVOI − baseline):
  - vs B0-AllEvidence: difference -0.9357 [95% CI -0.9667, -0.9060], wilcoxon p=0, Holm p=0 (statistically significant)
  - vs B1-FixedChecklist: difference -0.3540 [95% CI -0.3813, -0.3278], wilcoxon p=1.08e-138, Holm p=6.47e-138 (statistically significant)
  - vs B2-Random: difference -0.4333 [95% CI -0.4531, -0.4137], wilcoxon p=5.7e-230, Holm p=4.56e-229 (statistically significant)
  - vs B3-CheapestFirst: difference -0.3149 [95% CI -0.3405, -0.2908], wilcoxon p=5.8e-127, Holm p=2.9e-126 (statistically significant)
  - vs B4-InformationGain: difference -0.1803 [95% CI -0.1972, -0.1634], wilcoxon p=7.24e-99, Holm p=2.17e-98 (statistically significant)
  - vs B5-GenericVOI: difference +0.2734 [95% CI +0.2504, +0.2965], wilcoxon p=1.11e-111, Holm p=4.43e-111 (statistically significant)
  - vs B6-ConfidenceThreshold: difference -0.3916 [95% CI -0.4191, -0.3654], wilcoxon p=2.33e-166, Holm p=1.63e-165 (statistically significant)
  - vs B7-MyopicCostSensitiveVOI: difference +0.0735 [95% CI +0.0568, +0.0909], wilcoxon p=2.49e-16, Holm p=4.98e-16 (statistically significant)
  - vs B7b-Lookahead2VOI: difference +0.0394 [95% CI +0.0253, +0.0536], wilcoxon p=0.167, Holm p=0.167 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)

**AIT-LDS v2.0 replay (Layer B)** — AVOI: mean acquisitions 0.566 [0.525, 0.608], normalised cost 0.0232 [0.0196, 0.0276], expected loss 1.4766.
- Paired difference in acquisitions (AVOI − baseline):
  - vs B0-AllEvidence: difference -9.4340 [95% CI -9.4748, -9.3919], wilcoxon p=0, Holm p=0 (statistically significant)
  - vs B1-FixedChecklist: difference -1.5334 [95% CI -1.6237, -1.4444], wilcoxon p=1.77e-100, Holm p=1.06e-99 (statistically significant)
  - vs B2-Random: difference -1.3842 [95% CI -1.4663, -1.3027], wilcoxon p=3.57e-97, Holm p=1.78e-96 (statistically significant)
  - vs B3-CheapestFirst: difference -1.5104 [95% CI -1.5972, -1.4219], wilcoxon p=6.66e-101, Holm p=5.32e-100 (statistically significant)
  - vs B4-InformationGain: difference -0.6953 [95% CI -0.7665, -0.6280], wilcoxon p=3.65e-53, Holm p=1.46e-52 (statistically significant)
  - vs B5-GenericVOI: difference -0.0356 [95% CI -0.0447, -0.0269], wilcoxon p=2.67e-14, Holm p=2.67e-14 (statistically significant)
  - vs B6-ConfidenceThreshold: difference -1.5464 [95% CI -1.6345, -1.4566], wilcoxon p=1.03e-100, Holm p=7.22e-100 (statistically significant)
  - vs B7-MyopicCostSensitiveVOI: difference -0.2448 [95% CI -0.2856, -0.2027], wilcoxon p=7.34e-24, Holm p=1.47e-23 (statistically significant)
  - vs B7b-Lookahead2VOI: difference -0.0734 [95% CI -0.0872, -0.0603], wilcoxon p=4.84e-25, Holm p=1.45e-24 (statistically significant)
- Paired difference in normalised cost (AVOI − baseline):
  - vs B0-AllEvidence: difference -2.0310 [95% CI -2.1027, -1.9626], wilcoxon p=0, Holm p=0 (statistically significant)
  - vs B1-FixedChecklist: difference -0.3151 [95% CI -0.3394, -0.2909], wilcoxon p=4.94e-96, Holm p=3.95e-95 (statistically significant)
  - vs B2-Random: difference -0.2842 [95% CI -0.3089, -0.2602], wilcoxon p=4.94e-96, Holm p=3.95e-95 (statistically significant)
  - vs B3-CheapestFirst: difference -0.2460 [95% CI -0.2721, -0.2204], wilcoxon p=4.93e-96, Holm p=3.95e-95 (statistically significant)
  - vs B4-InformationGain: difference -0.2278 [95% CI -0.2533, -0.2028], wilcoxon p=1.29e-50, Holm p=5.17e-50 (statistically significant)
  - vs B5-GenericVOI: difference -0.0032 [95% CI -0.0067, -0.0004], wilcoxon p=0.823, Holm p=0.823 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)
  - vs B6-ConfidenceThreshold: difference -0.3163 [95% CI -0.3408, -0.2922], wilcoxon p=4.94e-96, Holm p=3.95e-95 (statistically significant)
  - vs B7-MyopicCostSensitiveVOI: difference -0.0119 [95% CI -0.0191, -0.0053], wilcoxon p=2.51e-10, Holm p=5.02e-10 (statistically significant)
  - vs B7b-Lookahead2VOI: difference -0.0037 [95% CI -0.0060, -0.0018], wilcoxon p=1.03e-10, Holm p=3.1e-10 (statistically significant)

**CERT r4.2 replay (Layer B)** — AVOI: mean acquisitions 1.346 [1.299, 1.394], normalised cost 0.0074 [0.0066, 0.0083], expected loss 0.4407.
- Paired difference in acquisitions (AVOI − baseline):
  - vs B0-AllEvidence: difference -8.6543 [95% CI -8.7007, -8.6058], wilcoxon p=1.23e-181, Holm p=1.11e-180 (statistically significant)
  - vs B1-FixedChecklist: difference -2.8359 [95% CI -2.9639, -2.7059], wilcoxon p=4.27e-171, Holm p=3.41e-170 (statistically significant)
  - vs B2-Random: difference -4.2111 [95% CI -4.3194, -4.1031], wilcoxon p=3.67e-160, Holm p=1.84e-159 (statistically significant)
  - vs B3-CheapestFirst: difference -4.6419 [95% CI -4.7926, -4.4902], wilcoxon p=8.58e-166, Holm p=6.01e-165 (statistically significant)
  - vs B4-InformationGain: difference -0.4871 [95% CI -0.6089, -0.3653], wilcoxon p=8.95e-14, Holm p=8.95e-14 (statistically significant)
  - vs B5-GenericVOI: difference -0.4974 [95% CI -0.5769, -0.4221], wilcoxon p=1.43e-34, Holm p=2.85e-34 (statistically significant)
  - vs B6-ConfidenceThreshold: difference -4.5531 [95% CI -4.7152, -4.3911], wilcoxon p=1.43e-165, Holm p=8.59e-165 (statistically significant)
  - vs B7-MyopicCostSensitiveVOI: difference -0.5717 [95% CI -0.6481, -0.4954], wilcoxon p=1.91e-36, Holm p=5.72e-36 (statistically significant)
  - vs B7b-Lookahead2VOI: difference -0.7771 [95% CI -0.8782, -0.6780], wilcoxon p=1.43e-46, Holm p=5.72e-46 (statistically significant)
- Paired difference in normalised cost (AVOI − baseline):
  - vs B0-AllEvidence: difference -1.2993 [95% CI -1.3528, -1.2484], wilcoxon p=3.78e-160, Holm p=3.33e-159 (statistically significant)
  - vs B1-FixedChecklist: difference -0.2370 [95% CI -0.2706, -0.2053], wilcoxon p=3.7e-160, Holm p=3.33e-159 (statistically significant)
  - vs B2-Random: difference -0.6883 [95% CI -0.7217, -0.6549], wilcoxon p=3.78e-160, Holm p=3.33e-159 (statistically significant)
  - vs B3-CheapestFirst: difference -0.4452 [95% CI -0.4897, -0.4006], wilcoxon p=9.69e-154, Holm p=4.85e-153 (statistically significant)
  - vs B4-InformationGain: difference -0.1115 [95% CI -0.1371, -0.0867], wilcoxon p=2.8e-14, Holm p=5.6e-14 (statistically significant)
  - vs B5-GenericVOI: difference -0.0108 [95% CI -0.0155, -0.0069], wilcoxon p=9.83e-33, Holm p=3.93e-32 (statistically significant)
  - vs B6-ConfidenceThreshold: difference -0.5410 [95% CI -0.5879, -0.4948], wilcoxon p=3.7e-160, Holm p=3.33e-159 (statistically significant)
  - vs B7-MyopicCostSensitiveVOI: difference +0.0012 [95% CI +0.0006, +0.0020], wilcoxon p=0.057, Holm p=0.057 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)
  - vs B7b-Lookahead2VOI: difference -0.0299 [95% CI -0.0380, -0.0231], wilcoxon p=1.59e-19, Holm p=4.77e-19 (statistically significant)

## RQ2 — Assurance safety

**Controlled IAM testbed (Layer A)** — AVOI UAR 0.0094 [0.0027, 0.0175], FAR among approvals 0.0089, expected loss 0.3807 [0.3458, 0.4188].
- Absolute UAR difference (AVOI − baseline); relative difference in parentheses:
  - vs B0-AllEvidence (UAR 0.0081): +0.0013 [-0.0027, +0.0067] (relative +16.7%); mcnemar_exact p=1, Holm p=1
  - vs B1-FixedChecklist (UAR 0.0067): +0.0027 [-0.0040, +0.0094] (relative +40.0%); mcnemar_exact p=0.688, Holm p=1
  - vs B2-Random (UAR 0.0043): +0.0052 [+0.0008, +0.0107] (relative +122.2%); signflip_permutation p=0.034, Holm p=0.272
  - vs B3-CheapestFirst (UAR 0.0135): -0.0040 [-0.0108, +0.0027] (relative -30.0%); mcnemar_exact p=0.453, Holm p=1
  - vs B4-InformationGain (UAR 0.0094): +0.0000 [-0.0040, +0.0040] (relative +0.0%); mcnemar_exact p=1, Holm p=1
  - vs B5-GenericVOI (UAR 0.2024): -0.1930 [-0.2214, -0.1646] (relative -95.3%); mcnemar_exact p=6.55e-42, Holm p=5.89e-41
  - vs B6-ConfidenceThreshold (UAR 0.0162): -0.0067 [-0.0162, +0.0013] (relative -41.7%); mcnemar_exact p=0.227, Holm p=1
  - vs B7-MyopicCostSensitiveVOI (UAR 0.0054): +0.0040 [-0.0040, +0.0121] (relative +75.0%); mcnemar_exact p=0.508, Holm p=1
  - vs B7b-Lookahead2VOI (UAR 0.0094): +0.0000 [+0.0000, +0.0000] (relative +0.0%); mcnemar_exact p=1, Holm p=1
- Expected decision loss difference (AVOI − baseline):
  - vs B0-AllEvidence: difference +0.0651 [95% CI +0.0437, +0.0870], wilcoxon p=4.97e-14, Holm p=3.98e-13 (statistically significant)
  - vs B1-FixedChecklist: difference +0.0057 [95% CI -0.0224, +0.0349], wilcoxon p=0.855, Holm p=1 (not statistically significant)
  - vs B2-Random: difference +0.0134 [95% CI -0.0078, +0.0364], wilcoxon p=0.492, Holm p=1 (not statistically significant)
  - vs B3-CheapestFirst: difference -0.0349 [95% CI -0.0672, -0.0052], wilcoxon p=0.0143, Holm p=0.0716 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)
  - vs B4-InformationGain: difference +0.0276 [95% CI +0.0109, +0.0448], wilcoxon p=4.4e-07, Holm p=3.08e-06 (statistically significant)
  - vs B5-GenericVOI: difference -0.5682 [95% CI -0.6766, -0.4672], wilcoxon p=0.000243, Holm p=0.00146 (statistically significant)
  - vs B6-ConfidenceThreshold: difference -0.0198 [95% CI -0.0568, +0.0151], wilcoxon p=0.928, Holm p=1 (not statistically significant)
  - vs B7-MyopicCostSensitiveVOI: difference -0.1359 [95% CI -0.1745, -0.0958], wilcoxon p=1.64e-22, Holm p=1.48e-21 (statistically significant)
  - vs B7b-Lookahead2VOI: difference -0.0010 [95% CI -0.0089, +0.0068], wilcoxon p=0.793, Holm p=1 (not statistically significant)

**AIT-LDS v2.0 replay (Layer B)** — AVOI UAR 0.3047 [0.2733, 0.3360], FAR among approvals 0.1835, expected loss 1.4766 [1.3624, 1.5898].
- Absolute UAR difference (AVOI − baseline); relative difference in parentheses:
  - vs B0-AllEvidence (UAR 0.3140): -0.0093 [-0.0186, -0.0012] (relative -3.0%); mcnemar_exact p=0.0768, Holm p=0.461
  - vs B1-FixedChecklist (UAR 0.3035): +0.0012 [+0.0000, +0.0035] (relative +0.4%); mcnemar_exact p=1, Holm p=1
  - vs B2-Random (UAR 0.2988): +0.0059 [+0.0027, +0.0097] (relative +2.0%); signflip_permutation p=0.00095, Holm p=0.0076
  - vs B3-CheapestFirst (UAR 0.2942): +0.0105 [+0.0047, +0.0174] (relative +3.6%); mcnemar_exact p=0.00391, Holm p=0.0273
  - vs B4-InformationGain (UAR 0.3047): +0.0000 [+0.0000, +0.0000] (relative +0.0%); mcnemar_exact p=1, Holm p=1
  - vs B5-GenericVOI (UAR 0.4616): -0.1570 [-0.1826, -0.1337] (relative -34.0%); mcnemar_exact p=4.59e-41, Holm p=4.13e-40
  - vs B6-ConfidenceThreshold (UAR 0.3070): -0.0023 [-0.0070, +0.0023] (relative -0.8%); mcnemar_exact p=0.625, Holm p=1
  - vs B7-MyopicCostSensitiveVOI (UAR 0.3023): +0.0023 [+0.0000, +0.0058] (relative +0.8%); mcnemar_exact p=0.5, Holm p=1
  - vs B7b-Lookahead2VOI (UAR 0.3047): +0.0000 [+0.0000, +0.0000] (relative +0.0%); mcnemar_exact p=1, Holm p=1
- Expected decision loss difference (AVOI − baseline):
  - vs B0-AllEvidence: difference -0.0091 [95% CI -0.0430, +0.0230], wilcoxon p=0.0249, Holm p=0.124 (not statistically significant)
  - vs B1-FixedChecklist: difference +0.0074 [95% CI +0.0004, +0.0187], wilcoxon p=0.0389, Holm p=0.156 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)
  - vs B2-Random: difference +0.0209 [95% CI +0.0099, +0.0339], wilcoxon p=0.0016, Holm p=0.0112 (statistically significant)
  - vs B3-CheapestFirst: difference +0.0334 [95% CI +0.0126, +0.0586], wilcoxon p=0.0127, Holm p=0.076 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)
  - vs B4-InformationGain: difference +0.0004 [95% CI -0.0022, +0.0030], wilcoxon p=1, Holm p=1 (not statistically significant)
  - vs B5-GenericVOI: difference -0.4696 [95% CI -0.5560, -0.3884], wilcoxon p=1.4e-12, Holm p=1.12e-11 (statistically significant)
  - vs B6-ConfidenceThreshold: difference -0.0056 [95% CI -0.0221, +0.0100], wilcoxon p=1, Holm p=1 (not statistically significant)
  - vs B7-MyopicCostSensitiveVOI: difference +0.1007 [95% CI +0.0842, +0.1189], wilcoxon p=1.69e-32, Holm p=1.52e-31 (statistically significant)
  - vs B7b-Lookahead2VOI: difference +0.0000 [95% CI +0.0000, +0.0000], wilcoxon p=1, Holm p=1 (not statistically significant)

**CERT r4.2 replay (Layer B)** — AVOI UAR 0.0307 [0.0123, 0.0521], FAR among approvals 0.0204, expected loss 0.4407 [0.3684, 0.5232].
- Absolute UAR difference (AVOI − baseline); relative difference in parentheses:
  - vs B0-AllEvidence (UAR 0.0460): -0.0153 [-0.0307, -0.0031] (relative -33.3%); mcnemar_exact p=0.0625, Holm p=0.312
  - vs B1-FixedChecklist (UAR 0.0429): -0.0123 [-0.0245, -0.0031] (relative -28.6%); mcnemar_exact p=0.125, Holm p=0.5
  - vs B2-Random (UAR 0.0472): -0.0166 [-0.0262, -0.0086] (relative -35.1%); signflip_permutation p=5e-05, Holm p=0.0004
  - vs B3-CheapestFirst (UAR 0.0307): +0.0000 [+0.0000, +0.0000] (relative +0.0%); mcnemar_exact p=1, Holm p=1
  - vs B4-InformationGain (UAR 0.0307): +0.0000 [+0.0000, +0.0000] (relative +0.0%); mcnemar_exact p=1, Holm p=1
  - vs B5-GenericVOI (UAR 0.1564): -0.1258 [-0.1626, -0.0920] (relative -80.4%); mcnemar_exact p=9.09e-13, Holm p=8.19e-12
  - vs B6-ConfidenceThreshold (UAR 0.0613): -0.0307 [-0.0521, -0.0123] (relative -50.0%); mcnemar_exact p=0.00195, Holm p=0.0137
  - vs B7-MyopicCostSensitiveVOI (UAR 0.0307): +0.0000 [+0.0000, +0.0000] (relative +0.0%); mcnemar_exact p=1, Holm p=1
  - vs B7b-Lookahead2VOI (UAR 0.0583): -0.0276 [-0.0460, -0.0123] (relative -47.4%); mcnemar_exact p=0.00391, Holm p=0.0234
- Expected decision loss difference (AVOI − baseline):
  - vs B0-AllEvidence: difference -0.0279 [95% CI -0.0774, +0.0144], wilcoxon p=0.405, Holm p=1 (not statistically significant)
  - vs B1-FixedChecklist: difference -0.0361 [95% CI -0.0857, +0.0041], wilcoxon p=0.56, Holm p=1 (not statistically significant)
  - vs B2-Random: difference -0.0512 [95% CI -0.0902, -0.0149], wilcoxon p=0.106, Holm p=0.532 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)
  - vs B3-CheapestFirst: difference -0.0413 [95% CI -0.0681, -0.0134], wilcoxon p=0.0124, Holm p=0.0871 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)
  - vs B4-InformationGain: difference +0.0155 [95% CI +0.0000, +0.0310], wilcoxon p=0.0545, Holm p=0.327 (not statistically significant)
  - vs B5-GenericVOI: difference -0.3209 [95% CI -0.4417, -0.2095], wilcoxon p=0.00285, Holm p=0.0256 (statistically significant)
  - vs B6-ConfidenceThreshold: difference -0.1311 [95% CI -0.1961, -0.0702], wilcoxon p=0.00399, Holm p=0.0319 (statistically significant)
  - vs B7-MyopicCostSensitiveVOI: difference +0.0010 [95% CI -0.0144, +0.0165], wilcoxon p=0.903, Holm p=1 (not statistically significant)
  - vs B7b-Lookahead2VOI: difference -0.0960 [95% CI -0.1641, -0.0372], wilcoxon p=0.115, Holm p=0.532 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)

## RQ3 — Governed autonomy (risk–coverage / escalation)

**Controlled IAM testbed (Layer A)** — area under the UAR–coverage curve (lower is better): AVOI 0.0024, B1-FixedChecklist 0.0052, B3-CheapestFirst 0.0052, B4-InformationGain 0.0061, B6-ConfidenceThreshold 0.0829, B7b-Lookahead2VOI 0.0053, B2-Random 0.0042. AVOI at its tuned threshold: coverage 0.761, escalation rate 0.239. Single-point methods without escalation (B5, B7) have coverage 1 by construction: B5 UAR 0.2024, B7 UAR 0.0054.
  - AVOI target:coverage=0.6: partially achieved (11/30 folds); UAR 0.000 [0.000, 0.000]; coverage 0.543 [0.507, 0.580]; acquisitions 1.575 [1.510, 1.643]
  - AVOI target:coverage=0.7: partially achieved (7/30 folds); UAR 0.014 [0.000, 0.033]; coverage 0.643 [0.598, 0.688]; acquisitions 1.603 [1.518, 1.692]
  - AVOI target:coverage=0.8: partially achieved (12/30 folds); UAR 0.004 [0.000, 0.011]; coverage 0.811 [0.784, 0.839]; acquisitions 1.555 [1.496, 1.615]
  - AVOI target:coverage=0.9: partially achieved (15/30 folds); UAR 0.014 [0.003, 0.028]; coverage 0.884 [0.864, 0.904]; acquisitions 1.700 [1.634, 1.768]
  - B1-FixedChecklist target:coverage=0.6: partially achieved (17/30 folds); UAR 0.000 [0.000, 0.000]; coverage 0.608 [0.580, 0.637]; acquisitions 4.610 [4.536, 4.688]
  - B1-FixedChecklist target:coverage=0.7: partially achieved (16/30 folds); UAR 0.000 [0.000, 0.000]; coverage 0.676 [0.647, 0.704]; acquisitions 4.795 [4.713, 4.877]
  - B1-FixedChecklist target:coverage=0.8: partially achieved (17/30 folds); UAR 0.003 [0.000, 0.008]; coverage 0.790 [0.767, 0.814]; acquisitions 4.685 [4.612, 4.756]
  - B1-FixedChecklist target:coverage=0.9: partially achieved (20/30 folds); UAR 0.004 [0.000, 0.010]; coverage 0.882 [0.864, 0.899]; acquisitions 3.778 [3.695, 3.863]
  - B4-InformationGain target:coverage=0.6: partially achieved (14/30 folds); UAR 0.003 [0.000, 0.008]; coverage 0.535 [0.503, 0.568]; acquisitions 2.781 [2.663, 2.894]
  - B4-InformationGain target:coverage=0.7: partially achieved (10/30 folds); UAR 0.010 [0.000, 0.024]; coverage 0.647 [0.609, 0.683]; acquisitions 2.737 [2.608, 2.866]
  - B4-InformationGain target:coverage=0.8: partially achieved (16/30 folds); UAR 0.008 [0.000, 0.018]; coverage 0.802 [0.776, 0.826]; acquisitions 2.250 [2.150, 2.350]
  - B4-InformationGain target:coverage=0.9: partially achieved (20/30 folds); UAR 0.008 [0.002, 0.016]; coverage 0.880 [0.862, 0.897]; acquisitions 2.021 [1.939, 2.101]
  - B6-ConfidenceThreshold target:coverage=0.6: partially achieved (19/30 folds); UAR 0.078 [0.057, 0.102]; coverage 0.575 [0.549, 0.604]; acquisitions 4.729 [4.637, 4.817]
  - B6-ConfidenceThreshold target:coverage=0.7: partially achieved (14/30 folds); UAR 0.194 [0.154, 0.233]; coverage 0.709 [0.680, 0.737]; acquisitions 4.015 [3.893, 4.138]
  - B6-ConfidenceThreshold target:coverage=0.8: partially achieved (20/30 folds); UAR 0.082 [0.058, 0.106]; coverage 0.793 [0.771, 0.815]; acquisitions 4.305 [4.220, 4.389]
  - B6-ConfidenceThreshold target:coverage=0.9: partially achieved (19/30 folds); UAR 0.075 [0.050, 0.099]; coverage 0.880 [0.863, 0.897]; acquisitions 4.062 [3.979, 4.147]

**AIT-LDS v2.0 replay (Layer B)** — area under the UAR–coverage curve (lower is better): AVOI 0.2032, B1-FixedChecklist 0.2036, B3-CheapestFirst 0.1896, B4-InformationGain 0.2040, B6-ConfidenceThreshold 0.2207, B7b-Lookahead2VOI 0.1568, B2-Random 0.1964. AVOI at its tuned threshold: coverage 0.872, escalation rate 0.128. Single-point methods without escalation (B5, B7) have coverage 1 by construction: B5 UAR 0.4616, B7 UAR 0.3023.
  - AVOI target:coverage=0.6: partially achieved (1/4 folds); UAR 0.484 [0.442, 0.527]; coverage 0.479 [0.439, 0.519]; acquisitions 2.264 [2.153, 2.377]
  - AVOI target:coverage=0.7: not achieved (inner validation); UAR nan; coverage nan; acquisitions nan
  - AVOI target:coverage=0.8: not achieved (inner validation); UAR nan; coverage nan; acquisitions nan
  - AVOI target:coverage=0.9: partially achieved (1/4 folds); UAR 0.484 [0.442, 0.527]; coverage 0.490 [0.450, 0.530]; acquisitions 2.264 [2.153, 2.377]
  - B1-FixedChecklist target:coverage=0.6: partially achieved (1/4 folds); UAR 0.000 [0.000, 0.000]; coverage 0.700 [0.663, 0.738]; acquisitions 8.175 [8.009, 8.333]
  - B1-FixedChecklist target:coverage=0.7: partially achieved (1/4 folds); UAR 0.483 [0.440, 0.525]; coverage 0.502 [0.462, 0.543]; acquisitions 8.398 [8.253, 8.540]
  - B1-FixedChecklist target:coverage=0.8: partially achieved (2/4 folds); UAR 0.296 [0.265, 0.328]; coverage 0.708 [0.682, 0.734]; acquisitions 6.546 [6.375, 6.719]
  - B1-FixedChecklist target:coverage=0.9: partially achieved (2/4 folds); UAR 0.296 [0.265, 0.328]; coverage 0.753 [0.729, 0.778]; acquisitions 4.940 [4.723, 5.156]
  - B4-InformationGain target:coverage=0.6: partially achieved (2/4 folds); UAR 0.294 [0.263, 0.325]; coverage 0.602 [0.575, 0.630]; acquisitions 6.727 [6.553, 6.905]
  - B4-InformationGain target:coverage=0.7: not achieved (inner validation); UAR nan; coverage nan; acquisitions nan
  - B4-InformationGain target:coverage=0.8: partially achieved (2/4 folds); UAR 0.295 [0.264, 0.327]; coverage 0.717 [0.691, 0.742]; acquisitions 4.156 [3.976, 4.346]
  - B4-InformationGain target:coverage=0.9: achieved; UAR 0.301 [0.269, 0.334]; coverage 0.822 [0.806, 0.837]; acquisitions 3.328 [3.206, 3.451]
  - B6-ConfidenceThreshold target:coverage=0.6: partially achieved (2/4 folds); UAR 0.294 [0.263, 0.325]; coverage 0.647 [0.618, 0.674]; acquisitions 7.801 [7.677, 7.924]
  - B6-ConfidenceThreshold target:coverage=0.7: partially achieved (1/4 folds); UAR 0.488 [0.446, 0.531]; coverage 0.502 [0.462, 0.542]; acquisitions 8.450 [8.312, 8.583]
  - B6-ConfidenceThreshold target:coverage=0.8: partially achieved (2/4 folds); UAR 0.302 [0.271, 0.334]; coverage 0.709 [0.682, 0.735]; acquisitions 7.050 [6.909, 7.196]
  - B6-ConfidenceThreshold target:coverage=0.9: achieved; UAR 0.310 [0.279, 0.342]; coverage 0.755 [0.737, 0.773]; acquisitions 5.882 [5.741, 6.021]

**CERT r4.2 replay (Layer B)** — area under the UAR–coverage curve (lower is better): AVOI 0.0247, B1-FixedChecklist 0.0236, B3-CheapestFirst 0.0357, B4-InformationGain 0.0229, B6-ConfidenceThreshold 0.1247, B7b-Lookahead2VOI 0.0290, B2-Random 0.0296. AVOI at its tuned threshold: coverage 0.931, escalation rate 0.069. Single-point methods without escalation (B5, B7) have coverage 1 by construction: B5 UAR 0.1564, B7 UAR 0.0307.
  - AVOI target:coverage=0.6: partially achieved (4/5 folds); UAR 0.041 [0.021, 0.066]; coverage 0.549 [0.521, 0.577]; acquisitions 1.857 [1.769, 1.948]
  - AVOI target:coverage=0.7: partially achieved (4/5 folds); UAR 0.036 [0.015, 0.058]; coverage 0.723 [0.693, 0.753]; acquisitions 1.755 [1.669, 1.841]
  - AVOI target:coverage=0.8: partially achieved (3/5 folds); UAR 0.013 [0.000, 0.032]; coverage 0.875 [0.847, 0.900]; acquisitions 1.587 [1.500, 1.677]
  - AVOI target:coverage=0.9: partially achieved (4/5 folds); UAR 0.030 [0.011, 0.052]; coverage 0.864 [0.840, 0.887]; acquisitions 1.554 [1.485, 1.625]
  - B1-FixedChecklist target:coverage=0.6: achieved; UAR 0.031 [0.012, 0.052]; coverage 0.569 [0.541, 0.597]; acquisitions 6.518 [6.339, 6.695]
  - B1-FixedChecklist target:coverage=0.7: achieved; UAR 0.031 [0.012, 0.052]; coverage 0.699 [0.671, 0.728]; acquisitions 5.581 [5.397, 5.768]
  - B1-FixedChecklist target:coverage=0.8: achieved; UAR 0.037 [0.018, 0.058]; coverage 0.802 [0.777, 0.827]; acquisitions 4.839 [4.665, 5.012]
  - B1-FixedChecklist target:coverage=0.9: achieved; UAR 0.046 [0.025, 0.071]; coverage 0.912 [0.894, 0.930]; acquisitions 4.009 [3.871, 4.149]
  - B4-InformationGain target:coverage=0.6: achieved; UAR 0.031 [0.012, 0.052]; coverage 0.586 [0.559, 0.614]; acquisitions 5.499 [5.294, 5.703]
  - B4-InformationGain target:coverage=0.7: achieved; UAR 0.031 [0.012, 0.052]; coverage 0.706 [0.679, 0.733]; acquisitions 4.295 [4.074, 4.514]
  - B4-InformationGain target:coverage=0.8: achieved; UAR 0.031 [0.012, 0.052]; coverage 0.803 [0.779, 0.828]; acquisitions 3.090 [2.872, 3.300]
  - B4-InformationGain target:coverage=0.9: achieved; UAR 0.043 [0.021, 0.067]; coverage 0.910 [0.892, 0.928]; acquisitions 2.271 [2.103, 2.440]
  - B6-ConfidenceThreshold target:coverage=0.6: achieved; UAR 0.049 [0.028, 0.074]; coverage 0.586 [0.560, 0.613]; acquisitions 6.316 [6.143, 6.484]
  - B6-ConfidenceThreshold target:coverage=0.7: achieved; UAR 0.058 [0.034, 0.086]; coverage 0.686 [0.659, 0.713]; acquisitions 5.707 [5.525, 5.884]
  - B6-ConfidenceThreshold target:coverage=0.8: partially achieved (4/5 folds); UAR 0.099 [0.062, 0.136]; coverage 0.807 [0.779, 0.835]; acquisitions 4.755 [4.556, 4.955]
  - B6-ConfidenceThreshold target:coverage=0.9: partially achieved (4/5 folds); UAR 0.270 [0.215, 0.329]; coverage 0.865 [0.840, 0.889]; acquisitions 4.138 [3.955, 4.328]

## Conservative interpretation (computed from Table 8)

- **iam**: AVOI expected loss significantly LOWER than [B5-GenericVOI, B7-MyopicCostSensitiveVOI] and significantly HIGHER than [B0-AllEvidence, B4-InformationGain]; UAR significantly lower than [B5-GenericVOI], higher than [none]; acquisitions significantly fewer than [B0-AllEvidence, B1-FixedChecklist, B2-Random, B3-CheapestFirst, B4-InformationGain, B6-ConfidenceThreshold, B7b-Lookahead2VOI], more than [B5-GenericVOI, B7-MyopicCostSensitiveVOI].
- **ait**: AVOI expected loss significantly LOWER than [B5-GenericVOI] and significantly HIGHER than [B2-Random, B7-MyopicCostSensitiveVOI]; UAR significantly lower than [B5-GenericVOI], higher than [B2-Random, B3-CheapestFirst]; acquisitions significantly fewer than [B0-AllEvidence, B1-FixedChecklist, B2-Random, B3-CheapestFirst, B4-InformationGain, B5-GenericVOI, B6-ConfidenceThreshold, B7-MyopicCostSensitiveVOI, B7b-Lookahead2VOI], more than [none].
- **cert**: AVOI expected loss significantly LOWER than [B5-GenericVOI, B6-ConfidenceThreshold] and significantly HIGHER than [none]; UAR significantly lower than [B2-Random, B5-GenericVOI, B6-ConfidenceThreshold, B7b-Lookahead2VOI], higher than [none]; acquisitions significantly fewer than [B0-AllEvidence, B1-FixedChecklist, B2-Random, B3-CheapestFirst, B4-InformationGain, B5-GenericVOI, B6-ConfidenceThreshold, B7-MyopicCostSensitiveVOI, B7b-Lookahead2VOI], more than [none].
- **H5 caveat (IAM conflicting-evidence subset, n=1338)**: false assurances AVOI 7 vs A6 2 (exact McNemar p=0.0625); false non-assurances AVOI 91 vs A6 310. Escalation reduced unsafe autonomous decisions mainly by avoiding false NON-assurance; it did not reduce false assurance relative to the no-escalation variant, which (under the 10:2 loss) defaults to NotAssured when uncertain.
- **LLM planner**: see the secondary section; llama3.1:8b acquired almost every available evidence item, so its loss is not comparable to an efficient planner at equal acquisition budget.
- **AIT**: the TAN evidence model transfers poorly between the two testbeds (full-evidence ECE in Table 6); all methods share this model, so AIT results mostly reflect cross-testbed distribution shift rather than acquisition policy differences. AIT-INTRUSION has only 12 refuted windows.

## Deviations from the pre-registration

- **D1 (post-hoc, declared here):** the registered safety-target selection (lowest inner cost with inner UAR <= target) is satisfied trivially by thresholds that stop at t=0 and decide NotAssured for every episode (UAR does not penalise false non-assurance). Registered H1 and Table 5 are reported unchanged; Table 5b / Table 11b add a non-degenerate variant (additionally requiring inner tuning objective J <= 1.0, the value of escalating every episode). Post-hoc results cannot confirm the pre-registered hypothesis and are labelled exploratory.

Post-hoc H1 (non-degenerate matching, AVOI vs B1-FixedChecklist):
- iam UAR<=0.01: acquisitions 1.060 vs 3.112, diff -2.053 [-2.134, -1.975], Wilcoxon Holm p=1.65e-192, rank-biserial -0.999; UAR diff +0.0000 [-0.0044, +0.0044] (n=1728) -> supported (exploratory)
- iam UAR<=0.02: acquisitions 0.971 vs 3.276, diff -2.305 [-2.388, -2.224], Wilcoxon Holm p=5.78e-224, rank-biserial -1.000; UAR diff -0.0027 [-0.0081, +0.0027] (n=1920) -> supported (exploratory)
- iam UAR<=0.05: acquisitions 0.970 vs 3.154, diff -2.184 [-2.262, -2.107], Wilcoxon Holm p=5.78e-224, rank-biserial -1.000; UAR diff -0.0148 [-0.0243, -0.0067] (n=1920) -> supported (exploratory)
- ait UAR<=0.01: acquisitions 0.000 vs 0.000, diff +0.000 [+0.000, +0.000], Wilcoxon Holm p=1, rank-biserial 0.000; UAR diff +0.0000 [+0.0000, +0.0000] (n=2304) -> not testable - still degenerate (both methods acquire no evidence at the selected thresholds) (exploratory)
- ait UAR<=0.02: acquisitions 0.000 vs 0.000, diff +0.000 [+0.000, +0.000], Wilcoxon Holm p=1, rank-biserial 0.000; UAR diff +0.0000 [+0.0000, +0.0000] (n=2304) -> not testable - still degenerate (both methods acquire no evidence at the selected thresholds) (exploratory)
- ait UAR<=0.05: acquisitions 0.000 vs 0.000, diff +0.000 [+0.000, +0.000], Wilcoxon Holm p=1, rank-biserial 0.000; UAR diff +0.0000 [+0.0000, +0.0000] (n=2304) -> not testable - still degenerate (both methods acquire no evidence at the selected thresholds) (exploratory)
- cert UAR<=0.01: acquisitions 1.537 vs 6.780, diff -5.243 [-5.565, -4.916], Wilcoxon Holm p=2.25e-37, rank-biserial -1.000; UAR diff +0.0000 [+0.0000, +0.0000] (n=214) -> supported (exploratory)
- cert UAR<=0.02: acquisitions 1.537 vs 6.603, diff -5.065 [-5.383, -4.748], Wilcoxon Holm p=2.25e-37, rank-biserial -1.000; UAR diff +0.0000 [+0.0000, +0.0000] (n=214) -> supported (exploratory)
- cert UAR<=0.05: acquisitions 1.251 vs 3.424, diff -2.173 [-2.259, -2.094], Wilcoxon Holm p=1.58e-184, rank-biserial -0.995; UAR diff -0.0123 [-0.0245, -0.0031] (n=969) -> supported (exploratory)

## Pre-registered hypotheses

- **H1 (iam)**: not supported - registered operating point degenerate (both methods selected thresholds that stop at t=0 with zero acquisitions; see post-hoc deviation D1). UAR<=0.01: mean acquisitions diff 0.000 [0.000,0.000], Wilcoxon p_holm=1, r_rb=0.000, UAR diff upper bound 0.000 (n=1920) | UAR<=0.02: mean acquisitions diff 0.000 [0.000,0.000], Wilcoxon p_holm=1, r_rb=0.000, UAR diff upper bound 0.000 (n=1920) | UAR<=0.05: mean acquisitions diff 0.000 [0.000,0.000], Wilcoxon p_holm=1, r_rb=0.000, UAR diff upper bound 0.000 (n=1920)
- **H2 (iam)**: not supported. summary UAR diff (k=1..3) 0.0013 [-0.0004,0.0036] | k=1: UAR diff 0.0013, McNemar p_holm=1 | k=2: UAR diff 0.0013, McNemar p_holm=1 | k=3: UAR diff 0.0013, McNemar p_holm=1
- **H3 (iam)**: supported. coverage 0.6 (held-out 0.54 vs 0.60): UAR diff -0.0227 p_holm=0.03125; acq diff -2.871 p_holm=1.24e-112 | coverage 0.7 (held-out 0.60 vs 0.65): UAR diff -0.0073 p_holm=1; acq diff -2.850 p_holm=1.652e-55 | coverage 0.8 (held-out 0.81 vs 0.83): UAR diff -0.0667 p_holm=0.0002441; acq diff -2.613 p_holm=1.199e-88 | coverage 0.9 (held-out 0.88 vs 0.89): UAR diff -0.0547 p_holm=0.000824; acq diff -2.448 p_holm=1.397e-131 | AURC(UAR) AVOI=0.0024, B6=0.0829
- **H4 (iam)**: supported. vs B5-GenericVOI: UAR diff -0.1930 (discordant 1/144), McNemar p_holm=1.309e-41 | vs A1-NoAsymmetricLoss: UAR diff -0.0337 (discordant 3/28), McNemar p_holm=4.649e-06
- **H5 (iam)**: supported. conflicting evidence (n=1338): unsafe autonomous AVOI=98 vs A6=312, UAR 0.011 vs 0.003, McNemar p_holm=3.41e-58 | insufficient evidence (n=507): unsafe autonomous AVOI=46 vs A6=308, UAR 0.024 vs 0.024, McNemar p_holm=2.706e-74
- **H1 (ait)**: not supported - registered operating point degenerate (both methods selected thresholds that stop at t=0 with zero acquisitions; see post-hoc deviation D1). UAR<=0.01: mean acquisitions diff 0.000 [0.000,0.000], Wilcoxon p_holm=1, r_rb=0.000, UAR diff upper bound 0.000 (n=2304) | UAR<=0.02: mean acquisitions diff 0.000 [0.000,0.000], Wilcoxon p_holm=1, r_rb=0.000, UAR diff upper bound 0.000 (n=2304) | UAR<=0.05: mean acquisitions diff 0.000 [0.000,0.000], Wilcoxon p_holm=1, r_rb=0.000, UAR diff upper bound 0.000 (n=2304)
- **H2 (ait)**: not supported. summary UAR diff (k=1..3) 0.0000 [0.0000,0.0000] | k=1: UAR diff 0.0000, McNemar p_holm=1 | k=2: UAR diff 0.0000, McNemar p_holm=1 | k=3: UAR diff 0.0000, McNemar p_holm=1
- **H3 (ait)**: not supported. coverage 0.7: not testable | coverage 0.8: not testable | coverage 0.6 (held-out 0.48 vs 0.48): UAR diff 0.0019 p_holm=1; acq diff -6.248 p_holm=1.851e-100 | coverage 0.9 (held-out 0.49 vs 0.52): UAR diff -0.0155 p_holm=0.04297; acq diff -6.108 p_holm=1.955e-100 | AURC(UAR) AVOI=0.2032, B6=0.2207
- **H4 (ait)**: supported. vs B5-GenericVOI: UAR diff -0.1570 (discordant 0/135), McNemar p_holm=9.184e-41 | vs A1-NoAsymmetricLoss: UAR diff 0.0000 (discordant 0/0), McNemar p_holm=1
- **H5 (ait)**: supported (no conflict subset in this domain; insufficient-evidence subset used). insufficient evidence (n=288): unsafe autonomous AVOI=1 vs A6=35, UAR 0.004 vs 0.004, McNemar p_holm=1.164e-10
- **H1 (cert)**: not supported - registered operating point degenerate (both methods selected thresholds that stop at t=0 with zero acquisitions; see post-hoc deviation D1). UAR<=0.01: mean acquisitions diff 0.000 [0.000,0.000], Wilcoxon p_holm=1, r_rb=0.000, UAR diff upper bound 0.000 (n=969) | UAR<=0.02: mean acquisitions diff 0.000 [0.000,0.000], Wilcoxon p_holm=1, r_rb=0.000, UAR diff upper bound 0.000 (n=969) | UAR<=0.05: mean acquisitions diff 0.000 [0.000,0.000], Wilcoxon p_holm=1, r_rb=0.000, UAR diff upper bound 0.000 (n=969)
- **H2 (cert)**: not supported. summary UAR diff (k=1..3) 0.0000 [0.0000,0.0000] | k=1: UAR diff 0.0000, McNemar p_holm=1 | k=2: UAR diff 0.0000, McNemar p_holm=1 | k=3: UAR diff 0.0000, McNemar p_holm=1
- **H3 (cert)**: supported. coverage 0.6 (held-out 0.55 vs 0.61): UAR diff -0.0247 p_holm=0.03125; acq diff -4.272 p_holm=4.857e-127 | coverage 0.7 (held-out 0.72 vs 0.67): UAR diff -0.0291 p_holm=0.01562; acq diff -4.037 p_holm=3.766e-134 | coverage 0.8 (held-out 0.87 vs 0.81): UAR diff -0.0584 p_holm=0.01172; acq diff -3.090 p_holm=4.369e-100 | coverage 0.9 (held-out 0.91 vs 0.84): UAR diff -0.1011 p_holm=3.052e-05; acq diff -3.130 p_holm=1.017e-104 | AURC(UAR) AVOI=0.0247, B6=0.1247
- **H4 (cert)**: supported. vs B5-GenericVOI: UAR diff -0.1258 (discordant 0/41), McNemar p_holm=1.819e-12 | vs A1-NoAsymmetricLoss: UAR diff -0.0123 (discordant 0/4), McNemar p_holm=0.125
- **H5 (cert)**: supported (no conflict subset in this domain; insufficient-evidence subset used). insufficient evidence (n=176): unsafe autonomous AVOI=64 vs A6=91, UAR 0.000 vs 0.000, McNemar p_holm=1.49e-08

## Ablations (AVOI − ablation, expected loss and UAR)

- iam / expected_loss:
  - vs A1-NoAsymmetricLoss: difference -0.1729 [95% CI -0.2276, -0.1198], wilcoxon p=1.54e-10, Holm p=7.71e-10 (statistically significant)
  - vs A2-NoLearnedReliability: difference -0.3458 [95% CI -0.3797, -0.3099], wilcoxon p=6.63e-112, Holm p=5.31e-111 (statistically significant)
  - vs A3-NoCost: difference +0.0057 [95% CI +0.0021, +0.0099], wilcoxon p=0.00451, Holm p=0.00451 (statistically significant)
  - vs A4-NoPrivacy: difference +0.0115 [95% CI +0.0068, +0.0161], wilcoxon p=2.73e-06, Holm p=1.09e-05 (statistically significant)
  - vs A5-NoDelay: difference +0.0141 [95% CI +0.0083, +0.0203], wilcoxon p=5.02e-06, Holm p=1.51e-05 (statistically significant)
  - vs A6-NoEscalation: difference -0.1432 [95% CI -0.1812, -0.1057], wilcoxon p=8.22e-24, Holm p=5.75e-23 (statistically significant)
  - vs A7-EntropyInsteadOfRisk: difference -0.0083 [95% CI -0.0229, +0.0094], wilcoxon p=0.000786, Holm p=0.00157 (inconclusive: significant paired test but the 95% CI of the mean difference includes 0)
  - vs A8-NaiveBayesModel: difference -0.0437 [95% CI -0.0698, -0.0167], wilcoxon p=9.5e-12, Holm p=5.7e-11 (statistically significant)
- iam / UAR:
  - vs A1-NoAsymmetricLoss: difference -0.0337 [95% CI -0.0486, -0.0202], mcnemar_exact p=4.65e-06, Holm p=3.72e-05 (statistically significant)
  - vs A2-NoLearnedReliability: difference +0.0081 [95% CI +0.0027, +0.0148], mcnemar_exact p=0.0312, Holm p=0.219 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)
  - vs A3-NoCost: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A4-NoPrivacy: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A5-NoDelay: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A6-NoEscalation: difference +0.0027 [95% CI -0.0040, +0.0108], mcnemar_exact p=0.727, Holm p=1 (not statistically significant)
  - vs A7-EntropyInsteadOfRisk: difference +0.0027 [95% CI +0.0000, +0.0067], mcnemar_exact p=0.5, Holm p=1 (not statistically significant)
  - vs A8-NaiveBayesModel: difference +0.0067 [95% CI +0.0013, +0.0135], mcnemar_exact p=0.0625, Holm p=0.375 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)
- ait / expected_loss:
  - vs A1-NoAsymmetricLoss: difference -0.0026 [95% CI -0.0048, -0.0009], wilcoxon p=0.0312, Holm p=0.188 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)
  - vs A2-NoLearnedReliability: difference +1.1606 [95% CI +1.0486, +1.2721], wilcoxon p=1.72e-71, Holm p=1.38e-70 (statistically significant)
  - vs A3-NoCost: difference -0.0022 [95% CI -0.0113, +0.0030], wilcoxon p=0.75, Holm p=1 (not statistically significant)
  - vs A4-NoPrivacy: difference +0.0000 [95% CI +0.0000, +0.0000], wilcoxon p=1, Holm p=1 (not statistically significant)
  - vs A5-NoDelay: difference +0.0000 [95% CI +0.0000, +0.0000], wilcoxon p=1, Holm p=1 (not statistically significant)
  - vs A6-NoEscalation: difference +0.0981 [95% CI +0.0855, +0.1107], wilcoxon p=1.14e-39, Holm p=7.95e-39 (statistically significant)
  - vs A7-EntropyInsteadOfRisk: difference -0.0004 [95% CI -0.0013, +0.0000], wilcoxon p=1, Holm p=1 (not statistically significant)
  - vs A8-NaiveBayesModel: difference +0.0026 [95% CI -0.0009, +0.0061], wilcoxon p=0.157, Holm p=0.786 (not statistically significant)
- ait / UAR:
  - vs A1-NoAsymmetricLoss: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A2-NoLearnedReliability: difference +0.2907 [95% CI +0.2593, +0.3221], mcnemar_exact p=1.11e-75, Holm p=8.84e-75 (statistically significant)
  - vs A3-NoCost: difference -0.0012 [95% CI -0.0035, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A4-NoPrivacy: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A5-NoDelay: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A6-NoEscalation: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A7-EntropyInsteadOfRisk: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A8-NaiveBayesModel: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
- cert / expected_loss:
  - vs A1-NoAsymmetricLoss: difference -0.0351 [95% CI -0.0826, +0.0072], wilcoxon p=0.737, Holm p=1 (not statistically significant)
  - vs A2-NoLearnedReliability: difference -0.5593 [95% CI -0.6316, -0.4768], wilcoxon p=2.51e-89, Holm p=2.01e-88 (statistically significant)
  - vs A3-NoCost: difference +0.0000 [95% CI +0.0000, +0.0000], wilcoxon p=1, Holm p=1 (not statistically significant)
  - vs A4-NoPrivacy: difference +0.0072 [95% CI -0.0052, +0.0196], wilcoxon p=0.26, Holm p=1 (not statistically significant)
  - vs A5-NoDelay: difference +0.0031 [95% CI +0.0000, +0.0072], wilcoxon p=0.25, Holm p=1 (not statistically significant)
  - vs A6-NoEscalation: difference +0.0010 [95% CI -0.0144, +0.0165], wilcoxon p=0.903, Holm p=1 (not statistically significant)
  - vs A7-EntropyInsteadOfRisk: difference -0.0010 [95% CI -0.0186, +0.0165], wilcoxon p=0.911, Holm p=1 (not statistically significant)
  - vs A8-NaiveBayesModel: difference -0.0103 [95% CI -0.0299, +0.0083], wilcoxon p=0.292, Holm p=1 (not statistically significant)
- cert / UAR:
  - vs A1-NoAsymmetricLoss: difference -0.0123 [95% CI -0.0245, -0.0031], mcnemar_exact p=0.125, Holm p=0.875 (inconclusive: CI excludes 0 but the Holm-adjusted test is not significant)
  - vs A2-NoLearnedReliability: difference +0.0307 [95% CI +0.0123, +0.0521], mcnemar_exact p=0.00195, Holm p=0.0156 (statistically significant)
  - vs A3-NoCost: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A4-NoPrivacy: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A5-NoDelay: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A6-NoEscalation: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A7-EntropyInsteadOfRisk: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)
  - vs A8-NaiveBayesModel: difference +0.0000 [95% CI +0.0000, +0.0000], mcnemar_exact p=1, Holm p=1 (not statistically significant)

## Omnibus tests

- iam: Friedman χ²=68.203, p=3.42e-11, blocks=30, methods=10, Kendall W=0.253
- ait: Friedman χ²=12.589, p=0.182, blocks=4, methods=10, Kendall W=0.350
- cert: Friedman χ²=24.554, p=0.00351, blocks=5, methods=10, Kendall W=0.546

## Cross-dataset summary

Random-effects meta-analysis NOT performed: only 2 public datasets (AIT, CERT) were available; the protocol requires at least three compatible public datasets.
Per-dataset effects are reported separately; the macro-average rows in Table 3 average dataset-level estimates and do not pool raw episodes.

## Secondary: LLM-only planner

- AVOI: UAR 0.000 [0.000, 0.000]; loss 0.391 [0.331, 0.448]; acquisitions 1.591 [1.500, 1.685]; coverage 0.745 [0.701, 0.786] (IAM outer fold 0 only; model llama3.1:8b; invalid responses 0)
- AVOI(value-stop,bayes): UAR 0.000 [0.000, 0.000]; loss 0.281 [0.224, 0.339]; acquisitions 1.917 [1.810, 2.023]; coverage 0.875 [0.841, 0.906] (IAM outer fold 0 only; model llama3.1:8b; invalid responses 0)
- B8-LLMPlanner: UAR 0.000 [0.000, 0.000]; loss 0.305 [0.247, 0.365]; acquisitions 6.167 [6.099, 6.234]; coverage 0.852 [0.815, 0.885] (IAM outer fold 0 only; model llama3.1:8b; invalid responses 0)

## Generated artefacts

- results/tables/table1_dataset_provenance.csv (+ .md, .tex)
- results/tables/table2_objectives_actions.csv (+ .md, .tex)
- results/tables/table3_main_comparison.csv (+ .md, .tex)
- results/tables/table4_matched_coverage.csv (+ .md, .tex)
- results/tables/table5_matched_safety.csv (+ .md, .tex)
- results/tables/table6_calibration.csv (+ .md, .tex)
- results/tables/table7_ablation.csv (+ .md, .tex)
- results/tables/table8_statistical_significance.csv (+ .md, .tex)
- results/tables/table9_generalization.csv (+ .md, .tex)
- results/tables/table10_sensitivity.csv (+ .md, .tex)
- results/tables/table5b_matched_safety_nondegenerate.csv (+ .md, .tex)
- results/figures/risk_coverage_curve.pdf
- results/figures/risk_coverage_curve.png
- results/figures/cost_safety_frontier.pdf
- results/figures/cost_safety_frontier.png
- results/figures/budget_performance_curve.pdf
- results/figures/budget_performance_curve.png
- results/figures/calibration_curve.pdf
- results/figures/calibration_curve.png
- results/figures/acquisition_risk_trajectory.pdf
- results/figures/acquisition_risk_trajectory.png
- results/figures/evidence_request_ecdf.pdf
- results/figures/evidence_request_ecdf.png
- results/figures/privacy_safety_tradeoff.pdf
- results/figures/privacy_safety_tradeoff.png
- results/figures/missingness_robustness_curve.pdf
- results/figures/missingness_robustness_curve.png
- results/figures/missingness_uar_curve.pdf
- results/figures/missingness_uar_curve.png
- results/figures/roc_pr_curves.pdf
- results/figures/roc_pr_curves.png
- results/figures/sensitivity_heatmap_tau_fa.pdf
- results/figures/sensitivity_heatmap_tau_fa.png
- results/figures/action_frequency_heatmap.pdf
- results/figures/action_frequency_heatmap.png
- results/figures/cost_violin.pdf
- results/figures/cost_violin.png
- results/figures/decision_flow.pdf
- results/figures/decision_flow.png