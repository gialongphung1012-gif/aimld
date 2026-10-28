@echo off
cd /d "%~dp0"
echo AIMLD - Windows local setup
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher "py" not found. Install Python 3.11+ and select Add Python to PATH.
  pause
  exit /b 1
)
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency install failed. Check internet access and Python version.
  pause
  exit /b 1
)
if not exist instance mkdir instance
py -m flask --app aimld.app create-admin
if errorlevel 1 (
  echo Admin creation did not complete. You can rerun this file and follow prompts.
  pause
  exit /b 1
)
echo Starting AIMLD on http://127.0.0.1:9132
py -m flask --app aimld.app run --host 127.0.0.1 --port 9132
pause
