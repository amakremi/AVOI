# Reproducing experiment CSVs

## Requirements and inputs

Use Python 3.11 or newer. The full pipeline also requires Docker Compose for the controlled IAM testbed and internet access to obtain datasets. AIT and CERT downloads require about 22 GB of storage. Raw data are not included; access and licensing details are in [`DATASETS.md`](DATASETS.md).

Install the pinned environment with `requirements.lock.txt`. On Windows, `reproduce.ps1` creates the virtual environment, installs dependencies, prepares data, runs the experiments, and writes CSV analysis results. `reproduce.sh` provides the Linux/macOS path.

```powershell
.\reproduce.ps1
.\reproduce.ps1 -SkipLLM
```

If local processed data are already prepared, skip the data-building stages:

```powershell
.\reproduce.ps1 -SkipDownload -SkipTestbed -SkipPublicBuild -SkipLLM
```

## Experiment inputs and determinism

- `results/EXPERIMENT_FREEZE.json` records hashes of the primary experiment configuration, code, manifests, evidence stores, and labels. Experiment runners verify it before execution.
- Random seeds and bootstrap seeds are defined in `config/`, experiment runners, and the frozen files. Scenario seeds derive deterministically from the master seed and scenario identifiers.
- Experiment-level episode, budget, calibration, and tuning outputs are written as compressed CSV files under `results/raw/`.
- CSV analysis outputs are written under `results/tables/`, `results/stage2/tables/`, and `results/stage3/tables/`.
- Large datasets, processed evidence stores, raw episode outputs, and traces are generated locally and are not required to be committed.

Re-run analysis from saved raw CSV outputs with:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe experiments\run_statistics.py
.\.venv\Scripts\python.exe experiments\run_stage2_csvs.py
.\.venv\Scripts\python.exe experiments\stage3\run_stage3_csvs.py
```

The Stage 2 and Stage 3 exporters require their corresponding raw CSV outputs and frozen JSON inputs to exist first.
