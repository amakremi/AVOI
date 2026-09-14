# AVOI-GRC end-to-end reproduction (Windows 11, PowerShell 5.1+, Docker Desktop, Python 3.11+).
# Stages can be skipped with switches. Expected wall time on a 28-thread laptop: downloads ~1 h (17 GB AIT + 5 GB CERT),
# testbed ~45 min, experiments ~25 min, statistics ~20 min.
param(
    [switch]$SkipDownload, [switch]$SkipTestbed, [switch]$SkipPublicBuild, [switch]$SkipExperiments, [switch]$SkipLLM,
    [int]$Workers = 22
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = ".\.venv\Scripts\python.exe"
function Step($name, [scriptblock]$block) { Write-Host "=== $name ===" -ForegroundColor Cyan; & $block; if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "$name failed ($LASTEXITCODE)" } }

Step "Python environment" {
    if (-not (Test-Path $py)) { python -m venv .venv }
    & $py -m pip install --upgrade pip -q
    & $py -m pip install -r requirements.lock.txt -q
}
$env:PYTHONPATH = "src"

if (-not $SkipDownload) {
    Step "Download datasets (official sources, checksums, manifest)" { & $py data\download_datasets.py }
    Step "Extract CERT r4.2" { New-Item -ItemType Directory -Force data\raw\cert\r4.2_extracted | Out-Null; tar -xjf data\raw\cert\r4.2.tar.bz2 -C data\raw\cert\r4.2_extracted }
}
Step "Requirement grounding (NIST 800-53A, SCF, NCA ECC)" { & $py src\avoi\datasets\grounding.py }

if (-not $SkipTestbed) {
    Step "Start Docker testbed" { docker compose up -d }
    Step "Wait for Keycloak" { for ($i = 0; $i -lt 120; $i++) { try { if ((Invoke-WebRequest http://127.0.0.1:58080/realms/master -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { break } } catch {}; Start-Sleep 3 } }
    Step "Generate, apply, collect and label 320 IAM scenarios" { & $py -m testbed.run_testbed --start 0 --end 320 --keep-realms 2 --skip-existing }
}
if (-not $SkipPublicBuild) {
    Step "AIT-LDS v2.0 index + episodes" { & $py src\avoi\datasets\ait.py; & $py -m avoi.datasets.ait_episodes }
    Step "CERT r4.2 stores + episodes" { & $py -m avoi.datasets.cert }
}
Step "Unit, integration and leakage tests" { & $py -m pytest tests -q -p no:cacheprovider }
if (-not (Test-Path results\EXPERIMENT_FREEZE.json)) { Step "Freeze experimental configuration" { & $py experiments\freeze_experiment.py } }
if (-not $SkipExperiments) {
    Step "Primary nested validation (IAM)" { & $py experiments\run_primary.py --workers $Workers }
    Step "Public replay (AIT, CERT)" { & $py experiments\run_public_replay.py --workers $Workers }
    Step "Ablations" { & $py experiments\run_ablation.py --workers $Workers }
    Step "Sensitivity + leave-one-family-out" { & $py experiments\run_sensitivity.py --workers $Workers }
}
if (-not $SkipLLM) { Step "Secondary LLM planner (requires Ollama + llama3.1:8b)" { & $py experiments\run_llm_planner.py --model llama3.1:8b --fold 0 } }
Step "Live agent demonstration on running testbed" { & $py experiments\live_agent_demo.py }
Step "Statistics, tables, figures, reports" { & $py experiments\run_statistics.py }
Step "Environment report and manifests" { & $py experiments\environment_report.py }
Write-Host "Done. See results\final_report\RESULTS.md" -ForegroundColor Green
