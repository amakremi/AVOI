# Stage 3 code and data reuse

Stage 3 evaluates adaptive next-evidence selection and external-domain evidence models. Previously examined Stage 1 and Stage 2 data are treated as development data; they are not counted as independent confirmation data.

## Reused components

- The decision rule, asymmetric Bayes risk, acquisition costs, evidence models, and adequacy policy are implemented in `src/avoi/`.
- The sequential agent, action admissibility, and evidence acquisition interface are shared with earlier experiment stages.
- The Docker IAM testbed, scenario generator, collectors, and ground-truth oracle are shared from `testbed/`.
- Dataset importers and feature construction are shared from `src/avoi/datasets/`.
- Grouped bootstrap, paired comparisons, and statistical tests are implemented in `src/avoi/evaluation/`.

## Run Stage 3

Prepare the development, validation, and confirmation inputs described by `config/stage3.yaml` and `docs/STAGE3_EXTERNAL_MODELS.md`. Then use the Stage 3 runner:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe experiments\stage3\run_stage3.py freeze
.\.venv\Scripts\python.exe experiments\stage3\run_stage3.py adequacy
.\.venv\Scripts\python.exe experiments\stage3\run_stage3.py confirm
.\.venv\Scripts\python.exe experiments\stage3\run_stage3_csvs.py
```

The analysis exporter writes CSV files under `results/stage3/tables/`.
