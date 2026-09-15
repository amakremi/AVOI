# Leakage controls

| Risk | Control | Automated test |
|---|---|---|
| Test labels reach the planner | Policies only receive an `EvidenceEnvironment` (available actions, acquired evidence, `acquire`) and a model fitted on training folds; `ObjectiveData` contains no labels; labels are loaded only by `avoi/evaluation/labels.py` | `test_test_labels_cannot_influence_planner` (scrambling test labels leaves traces identical); `test_planner_and_evidence_modules_never_import_labels` (AST import scan) |
| Ground-truth / answer-key files used as evidence | IAM oracle outputs in `data/processed/iam/ground_truth`, hidden systems of record in `testbed/state/hidden` (never served, never read by collectors); AIT label files resolved only into `data/processed/ait/ground_truth`; CERT answer key read only by label builder | `test_collectors_never_read_hidden_state_or_database`; `test_evidence_loaders_do_not_open_ground_truth` (file-open guard); `test_cert_store_contains_no_answer_key`; `test_ait_evidence_index_has_no_labels_and_excludes_attacker_hosts` |
| Red-team / attacker / simulator logs as evidence | AIT attacker_0, ext_user, internal/remote employee hosts excluded at indexing | same AIT test (host list check) |
| Unacquired evidence readable at t=0 | outcomes held in a private closure; public API exposes no arrays; double acquisition raises | `test_hidden_evidence_unreadable_until_acquired`; `test_trace_completeness_and_no_repeats` |
| Preprocessing fitted on test data | discretiser thresholds, cost/delay/privacy normalisers, TAN structure/CPTs, priors, reliability, calibration, hyperparameters and thresholds fitted on training (inner-training for tuning) episodes only | `test_preprocessing_fitted_on_training_fold_only` (modifying test evidence leaves all fitted objects unchanged); `test_calibration_isolated_from_test_data` |
| Same scenario/user/testbed in train and test | IAM grouped by scenario family; CERT grouped by user (a malicious scenario instance never straddles folds); AIT split by testbed; inner folds nested inside outer training | `test_outer_and_inner_splits_are_grouped` |
| Tuning on test | thresholds, target-matched points and hyperparameters from inner validation only; test curves are descriptive | code review + frozen configuration |
| Post-hoc changes | `results/EXPERIMENT_FREEZE.json` hashes configs, hypotheses, code, dataset manifest, evidence stores and ground truth; runners refuse to run on any change | `experiments/common.py::verify_freeze` |

Residual, documented label-derived elements: (i) the CERT case-control sampling and the insider flag used for
stratified splitting are derived from the answer key (never passed to policies); (ii) the AIT micro-claim boundaries
(which label types form EXFIL vs INTRUSION) were chosen after inspecting label temporal prevalence, before any method
was run; (iii) the adversarial-missingness condition hides the sources with the highest training-fold mutual
information with Y (training labels only).

## Stage-2 additions (evidence-model adequacy and confirmation)

| Risk | Control | Automated test |
|---|---|---|
| Confirmation labels influence adequacy status | adequacy computed only from the adequacy-validation partition; decisions frozen and hashed before confirmation; confirmation runner verifies the hash | `test_final_test_labels_cannot_influence_adequacy_or_calibration`, `test_confirmation_requires_frozen_adequacy_decisions` |
| Calibrator chosen on test data | model and calibrator selection use development out-of-fold posteriors only | same test (scrambling validation/confirmation labels leaves calibrator unchanged) |
| Thresholds hidden in code / tuned post hoc | policy thresholds read from `config/model_adequacy.yaml`, frozen in `EXPERIMENT_FREEZE_STAGE2.json`; sensitivity grid reported separately | `test_gate_thresholds_come_from_config` |
| Gate returns autonomous decisions for inadequate models | enforced agent returns HumanReview with MODEL_ADEQUACY_* reason and no acquisition | `test_inadequate_models_never_decide_autonomously` |
| Diagnostic mode contaminates enforced results | diagnostic and enforced runs are separate; enforced rows derived deterministically from the gate | `test_diagnostic_mode_equals_ungated_and_does_not_affect_enforced` |
| Stage-1 history modified | archive manifest hashes re-verified | `test_stage1_archive_unchanged_and_freeze_hash_preserved` |
| Development/validation/confirmation overlap | IAM new seed + family split; AIT separate testbeds; CERT separate release + user split (docs/STAGE2_DATA_INDEPENDENCE.md) | partition construction in `stage2.domain_partitions` |
