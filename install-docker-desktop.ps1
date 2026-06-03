$ErrorActionPreference = "Stop"

$InstallerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$InstallerPath = Join-Path $env:TEMP "Docker Desktop Installer.exe"

Write-Host "Docker Desktop installer yuklab olinmoqda..." -ForegroundColor Cyan
Write-Host $InstallerUrl

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $InstallerUrl -OutFile $InstallerPath

Write-Host "Docker Desktop per-user rejimda o'rnatilmoqda..." -ForegroundColor Cyan
Write-Host "Bu jarayon bir necha daqiqa davom etishi mumkin."

Start-Process -FilePath $InstallerPath -Wait -WindowStyle Hidden -ArgumentList @(
  "install",
  "--user",
  "--quiet",
  "--accept-license",
  "--backend=wsl-2",
  "--no-windows-containers"
)

Write-Host ""
Write-Host "Docker Desktop o'rnatish tugadi." -ForegroundColor Green
Write-Host "Docker Desktopni Start menyudan ishga tushiring, keyin real stackni ko'taring:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\start-real.ps1" -ForegroundColor Yellow
