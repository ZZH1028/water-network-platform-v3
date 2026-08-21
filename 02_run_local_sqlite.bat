@echo off
setlocal
cd /d "%~dp0"
set APP_ENV=development
set DEMO_MODE=true
set SEED_DEMO_DATA=true
set DATABASE_URL=sqlite:///%cd:\=/%/database/platform_dev.db

echo Starting Water Network Web Portal...
echo Local URL: http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
pause
