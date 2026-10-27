@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  set "BIOBRAIN_PY=python"
) else (
  set "BIOBRAIN_PY=py -3"
)
%BIOBRAIN_PY% -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11 or newer is required'"
if errorlevel 1 goto failed
if not exist ".venv\Scripts\python.exe" (
  %BIOBRAIN_PY% -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m streamlit run app.py --server.address=127.0.0.1 --browser.gatherUsageStats=false
if errorlevel 1 goto failed
exit /b 0
:failed
echo BioBrain could not start. Check Python installation, network access, and the error above.
pause
exit /b 1
