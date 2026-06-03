$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "Monitoring System real lokal stack ishga tushirilmoqda..." -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host ""
  Write-Host "Docker topilmadi. Real tizimni ishga tushirish uchun Docker Desktop kerak." -ForegroundColor Red
  Write-Host "O'rnatilgandan keyin shu buyruqni qayta bajaring:"
  Write-Host "  powershell -ExecutionPolicy Bypass -File .\start-real.ps1" -ForegroundColor Yellow
  exit 1
}

try {
  docker info | Out-Null
} catch {
  Write-Host ""
  Write-Host "Docker bor, lekin Docker Engine ishlamayapti. Docker Desktopni ishga tushiring." -ForegroundColor Red
  exit 1
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host ".env fayli .env.example asosida yaratildi. Parollarni tekshiring." -ForegroundColor Yellow
}

$port3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($port3000) {
  Write-Host "Diqqat: 3000-port band. Agar eski preview ochiq bo'lsa uni to'xtating." -ForegroundColor Yellow
}

docker compose up -d --build

Write-Host ""
Write-Host "Servislar holati:" -ForegroundColor Cyan
docker compose ps

Write-Host ""
Write-Host "Backend health tekshirilmoqda..." -ForegroundColor Cyan
$backendReady = $false
for ($i = 1; $i -le 30; $i++) {
  try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 3
    if ($response.status -eq "ok") {
      $backendReady = $true
      break
    }
  } catch {
    Start-Sleep -Seconds 2
  }
}

if (-not $backendReady) {
  Write-Host "Backend health hali tayyor emas. Loglarni ko'ring: docker compose logs -f backend" -ForegroundColor Yellow
} else {
  Write-Host "Backend tayyor." -ForegroundColor Green
}

Write-Host ""
Write-Host "Real tizim linklari:" -ForegroundColor Green
Write-Host "  Frontend:     http://127.0.0.1:3000/"
Write-Host "  Backend API:  http://127.0.0.1:8000/docs"
Write-Host "  Health:       http://127.0.0.1:8000/health"
Write-Host ""
Write-Host "Login:"
$adminUsername = (Select-String -Path ".env" -Pattern "^ADMIN_USERNAME=" -ErrorAction SilentlyContinue | Select-Object -First 1).Line -replace "^ADMIN_USERNAME=", ""
$adminPassword = (Select-String -Path ".env" -Pattern "^ADMIN_PASSWORD=" -ErrorAction SilentlyContinue | Select-Object -First 1).Line -replace "^ADMIN_PASSWORD=", ""
Write-Host "  username: $adminUsername"
Write-Host "  password: $adminPassword"
Write-Host ""
Write-Host "ESXi serverlarni Admin panel orqali qo'shing."
