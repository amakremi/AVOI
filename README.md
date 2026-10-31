# AVOI: Value-of-Information-Guided Evidence Acquisition for Cybersecurity Assurance

AVOI is a research prototype for selecting cybersecurity assurance evidence under decision risk, acquisition cost, privacy exposure, delay, and human escalation.

The repository contains experiment code, configurations, data preparation tools, and CSV results. Public-dataset results are replay experiments on observable security-assurance micro-claims; they are not compliance decisions or certifications. Raw datasets are not redistributed. See [`docs/DATASETS.md`](docs/DATASETS.md) for source, access, and licensing details.

## Reproduce the results

Requirements: Windows 11 with PowerShell 5.1+ or Linux/macOS with Bash, Python 3.11+, Docker Compose for the controlled IAM testbed, internet access, and about 22 GB of storage for AIT and CERT downloads.

```powershell
git clone https://github.com/amakremi/AVOI-Value-of-Information-Guided-Evidence-Acquisition-for-Cybersecurity-Assurance.git
cd AVOI-Value-of-Information-Guided-Evidence-Acquisition-for-Cybersecurity-Assurance
.\reproduce.ps1
```

To omit the optional Ollama planner:

```powershell
.\reproduce.ps1 -SkipLLM
```

If the datasets and processed stores are already present, rerun the experiment and CSV analysis stages with:

```powershell
.\reproduce.ps1 -SkipDownload -SkipTestbed -SkipPublicBuild -SkipLLM
```

On Linux/macOS, run `./reproduce.sh`; set `SKIP_DOWNLOAD=1`, `SKIP_TESTBED=1`, or `SKIP_LLM=1` to skip those stages.

For a focused run, install the pinned environment and set the source path:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe experiments\run_primary.py --workers 4
```

Use `experiments/run_public_replay.py`, `run_ablation.py`, and `run_sensitivity.py` for the other primary experiment suites. Stage 2 and Stage 3 entry points are in `experiments/` and `experiments/stage3/`. CSV analysis exporters are `experiments/run_statistics.py`, `experiments/run_stage2_csvs.py`, and `experiments/stage3/run_stage3_csvs.py`.

Large raw inputs, processed stores, and episode-level outputs are rebuilt locally. Summary CSV results are written under `results/tables/`, `results/stage2/tables/`, and `results/stage3/tables/`. Frozen configuration hashes and data provenance are documented in [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) and [`docs/DATASETS.md`](docs/DATASETS.md).

Run the test suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

## Code map

- `src/avoi/` — agent, evidence models, acquisition policies, datasets, and CSV analysis
- `experiments/` — experiment runners and CSV exporters
- `config/` — objectives, evidence actions, costs, and experiment settings
- `testbed/` and `docker-compose.yml` — controlled IAM environment
- `data/` — dataset downloaders, manifests, and local processing
- `results/` — CSV results and machine-readable experiment freezes
- `docs/` — data, methods, leakage controls, limitations, and reproduction steps
