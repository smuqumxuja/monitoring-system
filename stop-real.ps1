$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host "Docker topilmadi." -ForegroundColor Red
  exit 1
}

docker compose down
Write-Host "Monitoring System real stack to'xtatildi." -ForegroundColor Green
