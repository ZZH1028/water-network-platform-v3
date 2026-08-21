@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .env.public (
  echo [缺少 .env.public]
  echo 请复制 .env.public.example 为 .env.public，修改数据库密码、SECRET_KEY 和 CLOUDFLARE_TUNNEL_TOKEN。
  pause
  exit /b 1
)
docker compose --env-file .env.public -f docker-compose.public.yml up -d --build
if errorlevel 1 (
  echo 公网 Docker 启动失败，请检查 Docker Desktop、.env.public 和 Tunnel Token。
  pause
  exit /b 1
)
echo.
echo 公网服务已启动。正式域名由 Cloudflare Tunnel 中配置的 Public Hostname 决定。
echo 使用下面命令查看状态：
echo docker compose --env-file .env.public -f docker-compose.public.yml ps
pause
