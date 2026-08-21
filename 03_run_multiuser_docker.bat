@echo off
setlocal
cd /d "%~dp0"
docker compose up --build -d
if errorlevel 1 (echo Docker start failed. Install and start Docker Desktop.&pause&exit /b 1)
echo Platform started: http://localhost:8501
start "" "http://localhost:8501"
pause
