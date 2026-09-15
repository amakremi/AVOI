# Stage 3 — reuse map

Stage 3 (adaptive next-evidence selection; external-domain adequacy) reuses Stage-1/2 components wherever this is
scientifically compatible. Previously examined data are **DEVELOPMENT DATA** in Stage 3 and are never presented as
independent confirmation data. Prior result folders (`results/stage1_ungated/`, `results/stage2/`,
`results/final_report_v2/`) are read-only; `results/archive/pre_stage3_snapshot/MANIFEST.json` hashes them (2,603 files)
and `test_previous_results_unchanged` re-verifies them.

| Component | Location | Classification | Notes |
|---|---|---|---|
| AVOI utility ΔR − λC − μP − νD, Bayes risk, asymmetric loss 10:2:1 | `src/avoi/avoi.py`, `src/avoi/bayes_risk.py` | REUSE UNCHANGED | byte-identical to commit 7bb325c (tested) |
| Acquisition cost / privacy / delay terms | `src/avoi/costs.py` | REUSE UNCHANGED | |
| Evidence reliability (learned CPTs), exact inference, P(O_a \| E) | `src/avoi/models/tan.py` | REUSE UNCHANGED | TAN predictive P(O_a \| E) is already history-conditioned by exact sum-product over the tree; Naive Bayes conditions on history only through P(Y \| E) |
| Calibrated logistic evidence model | `src/avoi/models/discriminative.py` | REUSE WITH EXTENSION | optional gradient-boosting posterior estimator for WP2 candidates |
| Sequential agent, stopping rule, HumanReview, terminal decisions, trace infrastructure, action admissibility, acquisition interface | `src/avoi/agent.py`, `src/avoi/actions.py` | REUSE WITH EXTENSION | one flag `frozen_order` (Frozen-Order AVOI) and per-step ranking fields (`ranking`, `adaptive_next_action`, `frozen_next_action`, `rank_reversal`, `history`); the adaptive selection path itself (`frozen_order=False`) is byte-for-byte the Stage-2 code path (tests compare it against a Stage-2-equivalent PolicyConfig on identical inputs) |
| Frozen-Order AVOI | `PolicyConfig(frozen_order=True)` | NEW (wrapper by configuration) | no duplicated AVOI engine |
| Baselines B0–B7b, Random | `src/avoi/evaluation/engine.py::method_suite` | REUSE UNCHANGED | re-tuned only on Stage-3 validation partitions, with the existing tuning code |
| Evidence-model adequacy gate (metrics, bootstrap, statuses, reasons, persistence) | `src/avoi/adequacy.py` | REUSE UNCHANGED | |
| Primary adequacy policy | `config/model_adequacy.yaml` | REUSE UNCHANGED | loaded directly; SHA-256 recorded in the Stage-3 freeze; thresholds tested unchanged |
| Calibrator candidates none / sigmoid / isotonic / beta | `adequacy.Calibrator`, `select_calibrator` | REUSE WITH EXTENSION | Stage-3 wrapper excludes non-monotone (decreasing) calibration maps as semantically invalid (defect found in Stage-2 AIT-EXFIL; `docs/STAGE3_EXTERNAL_MODELS.md`) |
| Stage-2 development / validation / confirmation pipeline functions (`develop`, `validate`, `partition_context`, `suite`, `trajectories`, `rows_at`, `tune`, `gate_rows`, `curve_counts`) | `src/avoi/evaluation/stage2.py` | REUSE UNCHANGED (called from Stage-3 modules with Stage-3 partitions) | |
| Statistics: group bootstrap, paired bootstrap, Wilcoxon, McNemar, sign-flip permutation, Holm | `stage2_tables.py`, `metrics.py`, `stage2_analysis.py` | REUSE UNCHANGED | new: history–action permutation test, fixed-horizon paired comparison |
| Table writers (CSV/MD/LaTeX), figure style (method colours/markers), plotting helpers | `stats_tables.write_table`, `figures.py`, `stage2_figures.py` | REUSE UNCHANGED | |
| IAM Docker testbed (Keycloak, Postgres, Linux host, evidence repo), collectors, oracle, applier, runner | `testbed/` | REUSE UNCHANGED / runner WITH EXTENSION | runner option `--quiet-labels` (no label counts in confirmation logs) |
| IAM scenario generator | `testbed/scenarios/generator.py` | REUSE WITH EXTENSION | optional `branching` section: balanced latent mechanisms per objective using the existing mechanism knobs; Stage-1/2 specs byte-identical (tested) |
| IAM objectives, action sets, outcome definitions | `config/assurance_objectives.yaml` | REUSE UNCHANGED | same action set for every branching subtype |
| IAM evidence-store loader | `src/avoi/datasets/iam.py::load_iam` | REUSE WITH EXTENSION | scenario-id prefix whitelist extended with `s3dev-`/`s3val-`/`s3conf-` (one line); parsing logic unchanged |
| Historical IAM episodes (Stage 1: 320 scenarios; Stage 2: 320) | `data/processed/iam*`, `data/processed/iam_stage2` | REUSE AS DEVELOPMENT DATA | no Docker re-runs |
| AIT parser/indexer, episode builder, micro-claims, features, labels | `src/avoi/datasets/ait.py`, `ait_episodes.py` | REUSE UNCHANGED | |
| AIT russellmitchell, santos, fox, harrison, wardbeck (raw + indexes + stores) | `data/raw/ait`, `data/processed/ait*` | REUSE AS DEVELOPMENT DATA | checksum/CRC-verified; not re-downloaded |
| AIT range-request subset tool | `data/ait_remote_subset.py` | REUSE WITH EXTENSION | `--manifest=` option (Stage-3 manifest) |
| AIT shaw, wheeler, wilson | official Zenodo record 5789064 | NEW DATA (untouched) | verified in the official file list |
| CERT importer, harmonisation rules, sampling rule, evidence actions | `src/avoi/datasets/cert.py` | REUSE WITH EXTENSION (release-specific schema handling only if required) | |
| CERT r4.2, r5.2 stores | `data/processed/cert`, `data/processed/cert_stage2` | REUSE AS DEVELOPMENT DATA | |
| CERT r4.1, r5.1, r6.1, r6.2 | official figshare article 12841247 | NEW DATA (untouched) | published MD5 verified after download |
| Historical Stage-2 evidence models / adequacy records | `results/stage2/adequacy/` | REUSE AS REFERENCE / ZERO-SHOT COMPARATORS | never overwritten; Stage-3 models are written to `results/stage3/models/` |
| LLM planner | `src/avoi/baselines/llm_planner.py` | NOT NEEDED | not part of the Stage-3 hypotheses |
| Stage-2 report generators | `stage2_tables.py`, `stage2_figures.py` | REUSE WITH EXTENSION (called by Stage-3 report modules) | outputs go to `results/stage3/` only |
| Parsed caches | `data/processed/*` stores, SQLite indexes | REUSE when the source checksum, preprocessing version, feature version and objective definition match | recorded in `results/stage3/manifests/cache_reuse.json` |
