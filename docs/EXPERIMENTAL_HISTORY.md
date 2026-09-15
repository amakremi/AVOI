# Experimental history

## Stage 1 — original ungated AVOI experiment (historical, unchanged)
* Designed and pre-registered (`docs/PREREGISTERED_HYPOTHESES.md`, H1–H5) before its final experiments; configuration
  frozen with combined SHA-256 `4370311ede64cd3215fc4bc3ceeddbbbcef4a66453697b0595d80f1bca7715c8`; code at git commit
  `7bb325ceff9629709642ce9f6cf85039002f2eac`.
* Scale: controlled IAM 320 live scenarios × 6 objectives = 1,920 episodes (37 actions); AIT-LDS v2.0 2,304 replay
  episodes (testbeds russellmitchell, santos); CERT r4.2 969 replay episodes; 474 experiment tasks, 0 failures; 48/48 tests.
* **No evidence-model adequacy condition existed.** All artefacts are archived in `results/stage1_ungated/` with a
  SHA-256 manifest. In those historical artefacts the method is displayed as "AVOI-GRC"; manuscript-facing copies in
  `results/stage1_ungated/manuscript/` change only the display label to "AVOI".
* Stage-1 outcomes (reported, not rewritten): strong acquisition-efficiency gains; no universal safety improvement over
  strong baselines (information gain and all-evidence remained strong; all-evidence had lower IAM expected loss);
  asymmetric loss lowered unsafe assurance vs generic symmetric VOI; confidence-threshold stopping weaker than AVOI on
  IAM and CERT; AIT showed poor cross-testbed transfer/calibration; H1 not supported as registered (degenerate matched-
  safety definition; post-hoc correction exploratory); H2 not supported; H3 supported on IAM and CERT; H4 supported;
  H3 not supported on AIT; H5 supported as registered on all three datasets, with the recorded caveat that escalation
  mainly prevented false NON-assurance and did not reduce false assurance relative to the no-escalation variant.

## Why Stage 2 exists
Stage-1 AIT results exposed that the fitted evidence model transferred poorly between testbeds (full-evidence ECE ≈ 0.26,
calibration slope ≈ 0.19; false assurances with terminal belief ≥ 0.95). Because AVOI values evidence through
P(Y|E) and P(O_a|E), an inadequate evidence model makes AVOI values untrustworthy regardless of acquisition quality.
**This observation motivated the evidence-model adequacy safety condition. The adequacy mechanism was therefore NOT part
of the original pre-registration and must never be described as such.**

## Stage 2 — adequacy safety condition and confirmation
* Hypotheses S1–S4 (`docs/STAGE2_HYPOTHESES.md`) are prospective only relative to the Stage-2 frozen protocol.
* To avoid double dipping, Stage 2 uses data not used in Stage 1 wherever possible (`docs/STAGE2_DATA_INDEPENDENCE.md`):
  new live IAM scenarios (new seed), unused AIT-LDS testbeds, CERT release r5.2. Stage-1 data serve only as development
  (fitting/calibration) data.
* Order: policy + partitions + hypotheses frozen → development (model + calibrator selection on development out-of-fold
  predictions) → adequacy validation on a separate new-data partition → adequacy decisions frozen (hashed) →
  confirmation evaluation on a disjoint new-data partition.
* Stage-2 results can weaken Stage-1 conclusions; they do not change Stage-1 numbers or H1–H5 outcomes.
