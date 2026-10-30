@echo off
setlocal
cd /d "%~dp0\.."
if not exist .venv\Scripts\python.exe call ui\setup.cmd || exit /b 1
set HOST=127.0.0.1
set PORT=8501
start "" http://localhost:%PORT%
.venv\Scripts\python.exe -X utf8 -m streamlit run ui\app.py --server.address %HOST% --server.port %PORT% --server.headless true --browser.gatherUsageStats false
