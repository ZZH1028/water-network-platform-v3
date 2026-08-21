param([Parameter(Mandatory=$true)][string]$BackupFile)
$ErrorActionPreference = "Stop"
Get-Content -Raw $BackupFile | docker compose exec -T db pg_restore -U water_user -d water_platform --clean --if-exists
Write-Host "Restore completed."
