# AVOI-GRC — Value-of-Information-Guided Agentic Evidence Acquisition for Cybersecurity Compliance Assurance

Research prototype supporting a single contribution: **evidence acquisition for cybersecurity assurance formulated as a
sequential assurance decision problem**, where the next evidence action maximises the expected reduction in
assurance decision risk minus acquisition cost, privacy exposure and delay, with asymmetric false-assurance losses and
explicit human escalation.

This is **not** a GRC dashboard, an LLM evidence classifier, or a compliance-certification tool. Testbed predicates are
experimental operationalisations inspired by NIST SP 800-53/53A, NCA ECC-2:2024 and SCF; public-dataset results are
replay validations of evidence acquisition under observable security-assurance micro-claims, not compliance decisions.

## What is here
| Path | Content |
|---|---|
| `docker-compose.yml`, `testbed/` | controlled IAM assurance testbed (Keycloak, PostgreSQL, evidence repository, Linux host), scenario generator, evidence collectors, ground-truth oracle |
| `data/` | official-source downloaders (`download_datasets.py/.ps1`), dataset manifest, processed evidence stores and ground truth |
| `config/` | objectives, evidence actions, loss matrix, hyperparameter grids, experiments, scenario distribution |
| `src/avoi/` | AVOI agent, Bayes risk, AVOI computation, evidence models (TAN, calibrated LR), environments, costs/privacy, dataset loaders, baselines, evaluation engine, statistics, figures, reports |
| `experiments/` | freeze, primary, public replay, ablation, sensitivity, LLM planner, live demo, statistics, environment report |
| `tests/` | unit, integration and leakage tests |
| `results/` | raw episode-level outputs, traces, tables, figures, final report |
| `docs/` | datasets, methodology, leakage controls, pre-registered hypotheses, limitations, reproducibility |

## Quick start
```powershell
.\reproduce.ps1                # full pipeline (see docs/REPRODUCIBILITY.md)
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

## Results
See `results/final_report/RESULTS.md`, `CLAIMS_ALLOWED.md` (what the evidence does and does not support) and
`FAILURE_ANALYSIS.md`. Datasets that could not be used (Splunk BOTS v3 answer key, LANL cyber1) and why are documented in
`docs/DATASETS.md`; limitations in `docs/LIMITATIONS.md`.
