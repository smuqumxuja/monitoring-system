#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "Monitoring System real Linux deploy boshlanmoqda..."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker topilmadi. Ubuntu/Debian uchun:"
  echo "  sudo apt update"
  echo "  sudo apt install -y ca-certificates curl gnupg"
  echo "  curl -fsSL https://get.docker.com | sudo sh"
  echo "  sudo usermod -aG docker \$USER"
  echo "Keyin SSH sessiyani qayta oching."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin topilmadi. Docker Engine/Compose pluginni tekshiring."
  exit 1
fi

if [ ! -f ".env" ]; then
  cp ".env.production.example" ".env"
  if command -v openssl >/dev/null 2>&1; then
    SECRET_VALUE="$(openssl rand -hex 32)"
    DB_PASSWORD="$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-24)"
    ADMIN_PASSWORD="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-18)"
    sed -i "s|SECRET_KEY=replace-with-64-character-random-secret|SECRET_KEY=${SECRET_VALUE}|" ".env"
    sed -i "s|POSTGRES_PASSWORD=replace-with-strong-db-password|POSTGRES_PASSWORD=${DB_PASSWORD}|" ".env"
    sed -i "s|DATABASE_URL=postgresql+psycopg2://monitor:replace-with-strong-db-password@postgres:5432/monitoring|DATABASE_URL=postgresql+psycopg2://monitor:${DB_PASSWORD}@postgres:5432/monitoring|" ".env"
    sed -i "s|ADMIN_PASSWORD=replace-with-strong-admin-password|ADMIN_PASSWORD=${ADMIN_PASSWORD}|" ".env"
    echo ".env yaratildi. Admin parol: ${ADMIN_PASSWORD}"
  else
    echo ".env yaratildi. Iltimos SECRET_KEY, POSTGRES_PASSWORD va ADMIN_PASSWORD ni almashtiring."
    exit 1
  fi
fi

echo "Compose konfiguratsiya tekshirilmoqda..."
docker compose config >/dev/null

BACKEND_PORT_VALUE="$(grep '^BACKEND_PORT=' .env | cut -d= -f2- || true)"
FRONTEND_PORT_VALUE="$(grep '^FRONTEND_PORT=' .env | cut -d= -f2- || true)"
BACKEND_PORT_VALUE="${BACKEND_PORT_VALUE:-8000}"
FRONTEND_PORT_VALUE="${FRONTEND_PORT_VALUE:-3000}"

echo "Containerlar build qilinmoqda va ishga tushirilmoqda..."
docker compose up -d --build

echo "Backend health kutilyapti..."
for i in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT_VALUE}/health" >/dev/null 2>&1; then
    echo "Backend tayyor."
    break
  fi
  if [ "$i" -eq 40 ]; then
    echo "Backend health tayyor bo'lmadi. Loglar:"
    docker compose logs --tail=120 backend
    exit 1
  fi
  sleep 3
done

echo ""
docker compose ps
echo ""
echo "Real linklar:"
echo "  Frontend:    http://SERVER_IP:${FRONTEND_PORT_VALUE}/"
echo "  Backend API: http://SERVER_IP:${BACKEND_PORT_VALUE}/docs"
echo ""
echo "Login:"
echo "  username: $(grep '^ADMIN_USERNAME=' .env | cut -d= -f2-)"
echo "  password: $(grep '^ADMIN_PASSWORD=' .env | cut -d= -f2-)"
echo ""
echo "ESXi serverlarni Admin panel orqali qo'shing."
