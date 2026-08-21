@echo off
chcp 65001 >nul
cd /d "%~dp0"
docker compose --env-file .env.public -f docker-compose.public.yml down
pause
