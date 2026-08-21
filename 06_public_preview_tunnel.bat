@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo 水网工程水力调控智能平台 - 临时公网预览
echo ============================================================
echo.
where cloudflared >nul 2>nul
if errorlevel 1 (
  echo [未检测到 cloudflared]
  echo 请先下载安装 Cloudflare cloudflared 64-bit Windows 版本，
  echo 并确保 cloudflared.exe 已加入 PATH。
  echo 官方文档: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/
  echo.
  echo 安装完成后重新双击本文件。
  pause
  exit /b 1
)

echo 请确保 02_run_local_sqlite.bat 已经启动，且浏览器可访问 http://localhost:8501
echo.
echo 正在创建临时公网地址...
echo 生成后请复制终端中的 https://xxxxx.trycloudflare.com 地址。
echo 关闭本窗口后临时公网地址会失效。
echo.
cloudflared tunnel --url http://localhost:8501
pause
