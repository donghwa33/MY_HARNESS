@echo off
setlocal
cd /d "%~dp0\.."
where py >nul 2>nul && (py -3 -m venv .venv) || (python -m venv .venv)
if not exist .venv\Scripts\python.exe (
  echo Python 3 is required. Install it from python.org and run this again.
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
