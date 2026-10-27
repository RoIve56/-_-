@echo off
setlocal
cd /d "%~dp0"
rem Use a known supported 64-bit runtime, not whichever Python is newest.
py -3.12 -c "import sys,struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8" >nul 2>nul
if errorlevel 1 goto try_python
set "BIOBRAIN_PY=py -3.12"
goto runtime_ready
:try_python
python -c "import sys,struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8" >nul 2>nul
if errorlevel 1 goto need_python
set "BIOBRAIN_PY=python"
:runtime_ready
rem Keep an existing .venv intact; it may use an incompatible Python.
if exist ".venv-py312\Scripts\python.exe" goto check_venv
%BIOBRAIN_PY% -m venv .venv-py312
if errorlevel 1 goto failed
:check_venv
".venv-py312\Scripts\python.exe" -c "import sys,struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8"
if errorlevel 1 goto bad_venv
".venv-py312\Scripts\python.exe" -m pip install --upgrade --only-binary=:all: pip
if errorlevel 1 goto failed
rem Fail with a clear package error rather than compiling NumPy/Pandas locally.
".venv-py312\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements-windows.txt
if errorlevel 1 goto failed
".venv-py312\Scripts\python.exe" -m streamlit run app.py --server.address=127.0.0.1 --browser.gatherUsageStats=false
if errorlevel 1 goto failed
exit /b 0
:need_python
echo Install Python 3.12 for Windows, 64-bit, then run this file again.
echo Installer: https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
echo Enable the Python launcher and Add Python to PATH during installation.
pause
exit /b 1
:bad_venv
echo The .venv-py312 folder uses an incompatible Python. Rename that folder and try again.
pause
exit /b 1
:failed
echo BioBrain could not start. Please send the first package error shown above.
echo This launcher requires Python 3.12 64-bit and installs binary wheels only.
pause
exit /b 1
