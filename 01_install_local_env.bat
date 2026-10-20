@echo off
setlocal
cd /d "%~dp0"
set PIP_DISABLE_PIP_VERSION_CHECK=1

where py >nul 2>nul || (
  echo [ERROR] Python not found. Please install Python 3.11-3.13 first.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating virtual environment...
  py -m venv .venv || goto :failed
)

echo [2/3] Installing dependencies with HTTPS verification...
".venv\Scripts\python.exe" -m pip install -r requirements.txt --index-url https://pypi.org/simple
if errorlevel 1 goto :failed

echo [3/3] Preparing verified Cesium browser assets...
".venv\Scripts\python.exe" scripts\setup_scene_assets.py
if errorlevel 1 goto :failed

echo.
echo Environment ready.
echo Run 02_run_local_sqlite.bat to open the Web portal.
pause
exit /b 0

:failed
echo.
echo [ERROR] Dependency installation failed. Check network/proxy settings and retry.
pause
exit /b 1
