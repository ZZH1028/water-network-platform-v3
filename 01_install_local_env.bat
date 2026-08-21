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

echo [2/3] Installing dependencies from Aliyun PyPI mirror...
".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
if errorlevel 1 (
  echo.
  echo [WARN] Aliyun mirror failed. Retrying with TUNA mirror...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple --trusted-host mirrors.tuna.tsinghua.edu.cn
  if errorlevel 1 goto :failed
)

echo.
echo [3/3] Environment ready.
echo Run 02_run_local_sqlite.bat to open the Web portal.
pause
exit /b 0

:failed
echo.
echo [ERROR] Dependency installation failed. Check network/proxy settings and retry.
pause
exit /b 1
