@echo off
cd /d D:\PaperInprogress\AVOI\AVOI-Prototype
.venv\Scripts\python.exe experiments\run_primary.py --workers 22 || exit /b 1
.venv\Scripts\python.exe experiments\run_public_replay.py --workers 22 || exit /b 1
.venv\Scripts\python.exe experiments\run_ablation.py --workers 22 || exit /b 1
.venv\Scripts\python.exe experiments\run_sensitivity.py --workers 22 || exit /b 1
echo ALL_EXPERIMENTS_DONE
