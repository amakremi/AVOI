# Reproducibility

## Platform
Executed on Windows 11 Home (10.0.26200), Intel Core i7-14700HX (28 logical CPUs), 31.7 GB RAM, NVIDIA RTX 4070
Laptop GPU (8 GB; used only for the optional LLM planner), Docker Desktop 29.1.2 / Compose 2.40.3, Ollama 0.33.3,
CPython 3.14.2. Full details, package versions and execution timestamps: `environment_report.txt`.

**Windows Smart App Control** was enabled on the execution machine and blocked newly released unsigned native wheels
(numpy 2.5 random DLL, scipy 1.18, psycopg2). The environment therefore pins mature releases
(`requirements.txt`, exact freeze in `requirements.lock.txt`) and uses the pure-Python `pg8000` PostgreSQL driver.

## One-command reproduction
```powershell
.\reproduce.ps1                      # everything
.\reproduce.ps1 -SkipDownload -SkipTestbed -SkipPublicBuild   # re-run experiments + analysis from processed data
```
POSIX: `./reproduce.sh` (environment variables `SKIP_DOWNLOAD=1`, `SKIP_TESTBED=1`, `SKIP_LLM=1`).

## Determinism
* Seeds: `results/SEED_MANIFEST.json` (scenario seeds derived by SHA-256 from the master seed; random baseline seeds 0–19;
  CV `random_state`; initial-availability, degradation and bootstrap seeds).
* The IAM evidence store is deterministic given the scenario specification, except wall-clock acquisition times and
  absolute timestamps (history is time-shifted relative to the assessment time). Outcomes and labels are reproducible:
  the live demonstration re-acquired 20 evidence items from the running testbed with 0 outcome mismatches.
* LLM planner: temperature 0, seed 0, JSON-schema constrained; all prompts/responses cached in
  `results/raw/llm_planner/cache.jsonl`, so re-running replays cached responses exactly.
* `results/EXPERIMENT_FREEZE.json` holds SHA-256 hashes of configurations, hypotheses, core code, dataset manifest,
  evidence stores and ground truth; every experiment runner verifies them before running.

## Artefacts
* `data/DATASET_MANIFEST.json|csv` — provenance and checksums
* `results/EXPERIMENT_MANIFEST.json` — every task (474 main tasks), status and runtime
* `results/raw/<experiment>/<domain>/` — per-episode results, curves, budgets, tuning, calibration, model structures
* `results/traces/<domain>/<method>/` — complete JSON traces; `results/traces/live_demo/` — live testbed traces
* `results/tables/` (CSV/Markdown/LaTeX), `results/figures/` (PDF + 300-DPI PNG)
* `results/final_report/` — RESULTS.md, PAPER_RESULTS.tex, CLAIMS_ALLOWED.md, FAILURE_ANALYSIS.md, summary.json

## Licences of redistributed material
Raw datasets are not redistributed. AIT-LDS is CC BY-NC-SA 4.0 (non-commercial), CERT CC BY 4.0, BOTS v3 CC0,
NIST material public domain, NCA documents © NCA (used locally for grounding), SCF under its Creative Commons terms
(only identifiers are reproduced here).
