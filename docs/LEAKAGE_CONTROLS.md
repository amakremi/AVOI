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
