$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Force -Path backups | Out-Null
docker compose exec -T db pg_dump -U water_user -Fc water_platform > "backups\water_platform_$stamp.dump"
Write-Host "Backup created: backups\water_platform_$stamp.dump"
