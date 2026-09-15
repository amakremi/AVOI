# Claims allowed by the held-out results (auto-generated, conservative rules)

Rule: a claim is **supported** only when the paired comparison is statistically significant after Holm correction (p < 0.05) with a 95% CI excluding zero in the favourable direction on EVERY evaluated dataset; **partially supported** when this holds on some datasets only; otherwise **unsupported**. Statistical significance is not practical superiority; effect sizes are in Table 8.

## Supported claims

- AVOI-GRC achieves lower expected decision loss than B5-GenericVOI on every evaluated dataset: iam (-0.5682 [-0.6766, -0.4672]); ait (-0.4696 [-0.5560, -0.3884]); cert (-0.3209 [-0.4417, -0.2095])
- AVOI-GRC achieves lower unsafe assurance rate than B5-GenericVOI on every evaluated dataset: iam (-0.1930 [-0.2214, -0.1646]); ait (-0.1570 [-0.1826, -0.1337]); cert (-0.1258 [-0.1626, -0.0920])
- AVOI-GRC achieves fewer evidence acquisitions than B0-AllEvidence on every evaluated dataset: iam (-4.5286 [-4.5724, -4.4844]); ait (-9.4340 [-9.4748, -9.3919]); cert (-8.6543 [-8.7007, -8.6058])
- AVOI-GRC achieves fewer evidence acquisitions than B1-FixedChecklist on every evaluated dataset: iam (-2.8797 [-2.9443, -2.8161]); ait (-1.5334 [-1.6237, -1.4444]); cert (-2.8359 [-2.9639, -2.7059])
- AVOI-GRC achieves fewer evidence acquisitions than B2-Random on every evaluated dataset: iam (-2.1841 [-2.2370, -2.1319]); ait (-1.3842 [-1.4663, -1.3027]); cert (-4.2111 [-4.3194, -4.1031])
- AVOI-GRC achieves fewer evidence acquisitions than B3-CheapestFirst on every evaluated dataset: iam (-3.3714 [-3.4370, -3.3057]); ait (-1.5104 [-1.5972, -1.4219]); cert (-4.6419 [-4.7926, -4.4902])
- AVOI-GRC achieves fewer evidence acquisitions than B4-InformationGain on every evaluated dataset: iam (-0.6302 [-0.6885, -0.5745]); ait (-0.6953 [-0.7665, -0.6280]); cert (-0.4871 [-0.6089, -0.3653])
- AVOI-GRC achieves fewer evidence acquisitions than B6-ConfidenceThreshold on every evaluated dataset: iam (-3.0917 [-3.1578, -3.0255]); ait (-1.5464 [-1.6345, -1.4566]); cert (-4.5531 [-4.7152, -4.3911])
- AVOI-GRC achieves fewer evidence acquisitions than B7b-Lookahead2VOI on every evaluated dataset: iam (-0.2406 [-0.2781, -0.2036]); ait (-0.0734 [-0.0872, -0.0603]); cert (-0.7771 [-0.8782, -0.6780])
- AVOI-GRC achieves lower normalised acquisition cost than B0-AllEvidence on every evaluated dataset: iam (-0.9357 [-0.9667, -0.9060]); ait (-2.0310 [-2.1027, -1.9626]); cert (-1.2993 [-1.3528, -1.2484])
- AVOI-GRC achieves lower normalised acquisition cost than B1-FixedChecklist on every evaluated dataset: iam (-0.3540 [-0.3813, -0.3278]); ait (-0.3151 [-0.3394, -0.2909]); cert (-0.2370 [-0.2706, -0.2053])
- AVOI-GRC achieves lower normalised acquisition cost than B2-Random on every evaluated dataset: iam (-0.4333 [-0.4531, -0.4137]); ait (-0.2842 [-0.3089, -0.2602]); cert (-0.6883 [-0.7217, -0.6549])
- AVOI-GRC achieves lower normalised acquisition cost than B3-CheapestFirst on every evaluated dataset: iam (-0.3149 [-0.3405, -0.2908]); ait (-0.2460 [-0.2721, -0.2204]); cert (-0.4452 [-0.4897, -0.4006])
- AVOI-GRC achieves lower normalised acquisition cost than B4-InformationGain on every evaluated dataset: iam (-0.1803 [-0.1972, -0.1634]); ait (-0.2278 [-0.2533, -0.2028]); cert (-0.1115 [-0.1371, -0.0867])
- AVOI-GRC achieves lower normalised acquisition cost than B6-ConfidenceThreshold on every evaluated dataset: iam (-0.3916 [-0.4191, -0.3654]); ait (-0.3163 [-0.3408, -0.2922]); cert (-0.5410 [-0.5879, -0.4948])
- AVOI-GRC achieves lower privacy exposure than B0-AllEvidence on every evaluated dataset: iam (-0.1211 [-0.1257, -0.1169]); ait (-0.4859 [-0.4910, -0.4809]); cert (-0.6055 [-0.6128, -0.5975])
- AVOI-GRC achieves lower privacy exposure than B2-Random on every evaluated dataset: iam (-0.0544 [-0.0575, -0.0515]); ait (-0.0635 [-0.0677, -0.0594]); cert (-0.4065 [-0.4124, -0.4004])
- AVOI-GRC achieves lower privacy exposure than B3-CheapestFirst on every evaluated dataset: iam (-0.0524 [-0.0575, -0.0473]); ait (-0.0788 [-0.0841, -0.0735]); cert (-0.4305 [-0.4370, -0.4238])
- AVOI-GRC achieves lower privacy exposure than B4-InformationGain on every evaluated dataset: iam (-0.0390 [-0.0421, -0.0358]); ait (-0.0239 [-0.0268, -0.0211]); cert (-0.0208 [-0.0288, -0.0126])
- H3 on iam: supported
- H4 on iam: supported
- H5 on iam: supported — CAVEAT: the registered outcome counts unsafe AUTONOMOUS decisions (false assurance + false non-assurance); see RESULTS.md for whether escalation also lowered the false-assurance rate itself
- H4 on ait: supported
- H3 on cert: supported
- H4 on cert: supported

### Required context for the supported claims

- Efficiency claims versus B0-AllEvidence must be read together with AVOI-GRC's significantly HIGHER expected decision loss in: iam (+0.0651).
- Efficiency claims versus B2-Random must be read together with AVOI-GRC's significantly HIGHER expected decision loss in: ait (+0.0209).
- Efficiency claims versus B4-InformationGain must be read together with AVOI-GRC's significantly HIGHER expected decision loss in: iam (+0.0276).
- Efficiency claims versus B7-MyopicCostSensitiveVOI must be read together with AVOI-GRC's significantly HIGHER expected decision loss in: ait (+0.1007).

## Partially supported claims

- AVOI-GRC achieves lower expected decision loss than B6-ConfidenceThreshold: significant in cert (-0.1311 [-0.1961, -0.0702]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower expected decision loss than B7-MyopicCostSensitiveVOI: significant in iam (-0.1359 [-0.1745, -0.0958]); significantly WORSE in ait (+0.1007 [+0.0842, +0.1189]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower unsafe assurance rate than B2-Random: significant in cert (-0.0166 [-0.0262, -0.0086]); significantly WORSE in ait (+0.0059 [+0.0027, +0.0097]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower unsafe assurance rate than B6-ConfidenceThreshold: significant in cert (-0.0307 [-0.0521, -0.0123]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower unsafe assurance rate than B7b-Lookahead2VOI: significant in cert (-0.0276 [-0.0460, -0.0123]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves fewer evidence acquisitions than B5-GenericVOI: significant in ait (-0.0356 [-0.0447, -0.0269]); cert (-0.4974 [-0.5769, -0.4221]); significantly WORSE in iam (+0.6854 [+0.6333, +0.7375]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves fewer evidence acquisitions than B7-MyopicCostSensitiveVOI: significant in ait (-0.2448 [-0.2856, -0.2027]); cert (-0.5717 [-0.6481, -0.4954]); significantly WORSE in iam (+0.5625 [+0.4948, +0.6302]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower normalised acquisition cost than B5-GenericVOI: significant in cert (-0.0108 [-0.0155, -0.0069]); significantly WORSE in iam (+0.2734 [+0.2504, +0.2965]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower normalised acquisition cost than B7-MyopicCostSensitiveVOI: significant in ait (-0.0119 [-0.0191, -0.0053]); significantly WORSE in iam (+0.0735 [+0.0568, +0.0909]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower normalised acquisition cost than B7b-Lookahead2VOI: significant in ait (-0.0037 [-0.0060, -0.0018]); cert (-0.0299 [-0.0380, -0.0231]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower privacy exposure than B1-FixedChecklist: significant in ait (-0.0694 [-0.0741, -0.0648]); cert (-0.2379 [-0.2467, -0.2290]); significantly WORSE in iam (+0.0147 [+0.0084, +0.0210]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower privacy exposure than B5-GenericVOI: significant in cert (-0.0562 [-0.0649, -0.0482]); significantly WORSE in iam (+0.1260 [+0.1198, +0.1327]); ait (+0.0007 [+0.0003, +0.0010]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower privacy exposure than B6-ConfidenceThreshold: significant in ait (-0.0701 [-0.0748, -0.0654]); cert (-0.3628 [-0.3717, -0.3538]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower privacy exposure than B7-MyopicCostSensitiveVOI: significant in ait (-0.0080 [-0.0115, -0.0044]); cert (-0.0783 [-0.0902, -0.0663]); significantly WORSE in iam (+0.0589 [+0.0527, +0.0653]); not significant elsewhere among iam, ait, cert
- AVOI-GRC achieves lower privacy exposure than B7b-Lookahead2VOI: significant in ait (-0.0061 [-0.0077, -0.0046]); cert (-0.1006 [-0.1105, -0.0909]); significantly WORSE in iam (+0.0291 [+0.0247, +0.0334]); not significant elsewhere among iam, ait, cert
- H5 on ait: supported (no conflict subset in this domain; insufficient-evidence subset used) — CAVEAT: the registered outcome counts unsafe AUTONOMOUS decisions (false assurance + false non-assurance); see RESULTS.md for whether escalation also lowered the false-assurance rate itself
- H5 on cert: supported (no conflict subset in this domain; insufficient-evidence subset used) — CAVEAT: the registered outcome counts unsafe AUTONOMOUS decisions (false assurance + false non-assurance); see RESULTS.md for whether escalation also lowered the false-assurance rate itself

## Unsupported claims

- AVOI-GRC achieves lower expected decision loss than B0-AllEvidence (significantly worse in iam (+0.0651 [+0.0437, +0.0870]))
- AVOI-GRC achieves lower expected decision loss than B1-FixedChecklist (no dataset shows a significant improvement)
- AVOI-GRC achieves lower expected decision loss than B2-Random (significantly worse in ait (+0.0209 [+0.0099, +0.0339]))
- AVOI-GRC achieves lower expected decision loss than B3-CheapestFirst (no dataset shows a significant improvement)
- AVOI-GRC achieves lower expected decision loss than B4-InformationGain (significantly worse in iam (+0.0276 [+0.0109, +0.0448]))
- AVOI-GRC achieves lower expected decision loss than B7b-Lookahead2VOI (no dataset shows a significant improvement)
- AVOI-GRC achieves lower unsafe assurance rate than B0-AllEvidence (no dataset shows a significant improvement)
- AVOI-GRC achieves lower unsafe assurance rate than B1-FixedChecklist (no dataset shows a significant improvement)
- AVOI-GRC achieves lower unsafe assurance rate than B3-CheapestFirst (significantly worse in ait (+0.0105 [+0.0047, +0.0174]))
- AVOI-GRC achieves lower unsafe assurance rate than B4-InformationGain (no dataset shows a significant improvement)
- AVOI-GRC achieves lower unsafe assurance rate than B7-MyopicCostSensitiveVOI (no dataset shows a significant improvement)
- H1 on iam: not supported - registered operating point degenerate (both methods selected thresholds that stop at t=0 with zero acquisitions; see post-hoc deviation D1)
- H2 on iam: not supported
- H1 on ait: not supported - registered operating point degenerate (both methods selected thresholds that stop at t=0 with zero acquisitions; see post-hoc deviation D1)
- H2 on ait: not supported
- H3 on ait: not supported
- H1 on cert: not supported - registered operating point degenerate (both methods selected thresholds that stop at t=0 with zero acquisitions; see post-hoc deviation D1)
- H2 on cert: not supported
- AVOI-GRC automates or certifies regulatory compliance (NCA ECC, NIST, ISO): no compliance decision was evaluated; testbed predicates are experimental operationalisations and public-dataset labels are attack/insider micro-claims.
- AVOI-GRC outperforms human auditors: no human study was performed.
- AVOI-GRC yields real organisational audit cost savings: costs are testbed/replay measurements (records, bytes, seconds).
- Results generalise to real enterprise organisations: the IAM testbed is synthetic-but-live and the public corpora are testbed/synthetic datasets.
- Privacy exposure reductions correspond to reduced privacy risk: the exposure metric is a category-count proxy.
- Results hold for BOTS v3 or LANL: these datasets were not evaluated (access blockers documented).
- "AVOI-GRC outperforms all baselines" (expected loss): not established on every dataset for every baseline.