#!/usr/bin/env bash
# POSIX equivalent of reproduce.ps1 (Linux/macOS/Git-Bash). Requires Docker, Python 3.11+, tar with bzip2.
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python; [ -x "$PY" ] || PY=.venv/Scripts/python.exe
[ -x "$PY" ] || { python3 -m venv .venv; PY=.venv/bin/python; }
"$PY" -m pip install -r requirements.lock.txt -q
export PYTHONPATH=src
[ "${SKIP_DOWNLOAD:-0}" = 1 ] || { "$PY" data/download_datasets.py; mkdir -p data/raw/cert/r4.2_extracted; tar -xjf data/raw/cert/r4.2.tar.bz2 -C data/raw/cert/r4.2_extracted; }
"$PY" src/avoi/datasets/grounding.py
if [ "${SKIP_TESTBED:-0}" != 1 ]; then
  docker compose up -d
  until curl -sf http://127.0.0.1:58080/realms/master >/dev/null; do sleep 3; done
  "$PY" -m testbed.run_testbed --start 0 --end 320 --keep-realms 2 --skip-existing
fi
"$PY" src/avoi/datasets/ait.py && "$PY" -m avoi.datasets.ait_episodes && "$PY" -m avoi.datasets.cert
"$PY" -m pytest tests -q -p no:cacheprovider
[ -f results/EXPERIMENT_FREEZE.json ] || "$PY" experiments/freeze_experiment.py
"$PY" experiments/run_primary.py && "$PY" experiments/run_public_replay.py && "$PY" experiments/run_ablation.py && "$PY" experiments/run_sensitivity.py
[ "${SKIP_LLM:-0}" = 1 ] || "$PY" experiments/run_llm_planner.py --model llama3.1:8b --fold 0
"$PY" experiments/live_agent_demo.py
"$PY" experiments/run_statistics.py
"$PY" experiments/environment_report.py
