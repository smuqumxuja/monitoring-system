# Monitoring System

Markaz IT infratuzilmasi uchun ESXi hostlar, VM lar, network holati, alertlar va predictive risklarni kuzatadigan MVP monitoring tizimi.

## Texnologiyalar

- Backend: Python FastAPI
- Frontend: React + Tailwind + WebSocket + Recharts
- Database: PostgreSQL
- Cache/queue tayyor servisi: Redis
- ESXi integratsiya: pyVmomi
- SNMP monitoring: pysnmp
- Ping/latency: aioping
- Runtime: Docker Compose

## Servislar

Docker Compose quyidagi servislarni ishga tushiradi:

- `backend` - FastAPI API, JWT auth, WebSocket, admin endpointlar.
- `frontend` - React build, Nginx static server va `/api`, `/ws` reverse proxy.
- `postgres` - PostgreSQL database.
- `redis` - Redis service, keyingi queue/cache ishlari uchun tayyor.
- `worker` - ESXi collector va network monitor worker bir konteyner ichida.

## Loyiha strukturasi

```text
monitoring-system/
  backend/
    app/
      main.py
      config.py
      database.py
      models/
      schemas/
      routers/
      services/
      workers/
      utils/
    requirements.txt
    Dockerfile
    .dockerignore
  frontend/
    src/
      pages/
      components/
      services/
      hooks/
    package.json
    Dockerfile
    nginx.conf
    .dockerignore
  docker-compose.yml
  .env.example
  .env.production.example
  deploy-linux.sh
  .gitignore
  README.md
```

## Talablar

Serverda quyidagilar bo'lishi kerak:

- Docker Engine
- Docker Compose plugin

Windows kompyuterda Docker o'rnatilmagan bo'lsa, rasmiy Docker Desktop installer orqali o'rnatish uchun:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-docker-desktop.ps1
```

Installer per-user rejimda ishlaydi. Docker Desktop o'rnatilgandan keyin uni Start menyudan bir marta oching, license shartlarini tasdiqlang va engine ishga tushishini kuting.

Tekshirish:

```bash
docker --version
docker compose version
```

## Tez ishga tushirish

`monitoring-system` papkasida bitta komanda:

```bash
docker compose up -d --build
```

Windows kompyuterning o'zida real stackni ishga tushirish uchun:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-real.ps1
```

Bu skript Docker borligini tekshiradi, compose servislarini ko'taradi, backend health endpointini sinaydi va real linklarni chiqaradi.

Compose `.env` faylisiz ham default qiymatlar bilan ishga tushadi. Real muhit uchun `.env` yaratish tavsiya qilinadi:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Keyin ishga tushiring:

```bash
docker compose up -d --build
```

## Muhim sozlamalar

`.env` ichida kamida quyidagilarni almashtiring:

```env
SECRET_KEY=very-long-random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong-admin-password
POSTGRES_DB=monitoring
POSTGRES_USER=monitor
POSTGRES_PASSWORD=strong-db-password
```

Notification uchun:

```env
TELEGRAM_BOT_TOKEN=123456:token
TELEGRAM_CHAT_ID=123456789

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=monitoring@example.com
SMTP_PASSWORD=secret
SMTP_FROM=monitoring@example.com
SMTP_TO=admin@example.com
SMTP_USE_TLS=true
```

`SECRET_KEY` ESXi va notification secretlarini encrypt/decrypt qilishda ishlatiladi. Productionda uni o'zgartirib yubormang, aks holda eski encrypted parollar o'qilmaydi.

## URL lar

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/health

Default login, agar `.env` yaratilmagan bo'lsa:

- Username: `admin`
- Password: `change-me-now`

Real serverda `.env.production.example` asosida `.env` yarating yoki `deploy-linux.sh` ishlating. `deploy-linux.sh` admin parolni avtomatik generatsiya qilib terminalga chiqaradi.

## Smoke test

Servislar holati:

```bash
docker compose ps
```

Backend health:

```bash
curl http://localhost:8000/health
```

Windows PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Login token olish uchun avval captcha savolini oling:

```bash
curl http://localhost:8000/api/auth/captcha
```

Javobdagi `question` ni yechib, `captcha_token` va `captcha_answer` bilan login qiling:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=change-me-now&captcha_token=TOKEN&captcha_answer=ANSWER"
```

Frontendni oching:

```text
http://localhost:3000
```

Kutiladigan natija:

- `postgres` healthy.
- `redis` healthy.
- `backend` healthy va `/health` `{"status":"ok"}` qaytaradi.
- `frontend` login sahifasini ochadi.
- Login muvaffaqiyatli bo'lsa dashboard ochiladi.
- Dashboard WebSocket orqali `/ws/metrics` ga ulanadi.
- `worker` loglarida collector va network worker start bo'lgani ko'rinadi.

## Loglar

Backend loglari:

```bash
docker compose logs -f backend
```

Worker loglari:

```bash
docker compose logs -f worker
```

Frontend/Nginx loglari:

```bash
docker compose logs -f frontend
```

Barcha muhim exceptionlar logga yoziladi:

- API startup va unhandled exceptionlar
- ESXi ulanish va metric yig'ish xatolari
- ESXi VM parsing xatolari
- SNMP xatolari
- Ping kutubxonasi yoki OS permission xatolari
- Worker cycle xatolari
- WebSocket snapshot xatolari
- Telegram/email yuborish xatolari

## ESXi host qo'shish

1. Frontendga admin sifatida kiring.
2. `Admin` sahifasini oching.
3. ESXi host nomi, IP/hostname, username, password va portni kiriting.
4. Kerak bo'lsa SNMP checkboxni yoqing va community/portni kiriting.
5. Saqlang.

Worker keyingi siklda pyVmomi orqali ESXi hostga ulanadi va VM larni avtomatik aniqlaydi.

ESXi ulanishida xato bo'lsa:

- tizim yiqilmaydi;
- xato backend/worker logga yoziladi;
- databasega `esxi_connection` critical alert yoziladi;
- dashboardda alert chiqadi.

## Monitoring imkoniyatlari

Host bo'yicha:

- CPU total/used/usage
- RAM total/used/usage
- datastore total/free/usage
- datastore details
- NIC status
- network RX/TX
- uptime
- ping, latency, packet loss

VM bo'yicha:

- name
- power state
- CPU usage
- RAM usage
- disk size/usage
- IP address
- guest OS
- network RX/TX
- uptime
- ping, latency, packet loss
- monitoring enabled/disabled

## Network monitoring

Worker har `NETWORK_CHECK_INTERVAL_SECONDS` soniyada ESXi host va VM IP manzillarini ping qiladi. Default: `10` soniya.

Natijalar:

- `online` yoki `offline`
- latency ms
- packet loss
- consecutive failures
- last success time
- last checked time

Qoidalar:

- 3 marta ketma-ket javob bo'lmasa `uzilish ehtimoli` warning alert.
- 5 marta ketma-ket javob bo'lmasa `offline` critical alert.
- Ping tiklansa network alertlar avtomatik yopiladi.

Endpoint:

```text
GET /api/network/status
```

## Alert engine

Default thresholdlar:

- CPU > 85% holati 5 daqiqadan oshsa warning.
- CPU > 95% critical.
- RAM > 85% warning.
- RAM > 95% critical.
- Datastore free < 15% warning.
- Datastore free < 5% critical.
- VM offline bo'lsa critical.
- Ping latency > 100 ms warning.
- Packet loss > 10% warning.
- Packet loss > 30% critical.

Alertlar:

- databasega yoziladi;
- dashboardda ko'rinadi;
- Telegramga yuboriladi, agar sozlangan bo'lsa;
- emailga yuboriladi, agar SMTP sozlangan bo'lsa;
- cooldown bilan qayta-qayta yuborish cheklanadi.

Default cooldown:

```env
ALERT_COOLDOWN_SECONDS=300
```

Endpointlar:

```text
GET /api/alerts
PATCH /api/alerts/{alert_id}/ack
```

## Predictive monitoring

Tizim so'nggi 7 kunlik CPU/RAM/disk statistikasi asosida trend hisoblaydi.

Risklar:

- CPU/RAM usage 7 kun ichida 90% ga yetishi ehtimoli.
- VM disk usage 7 kun ichida 90% ga yetishi ehtimoli.
- Datastore 7 kun ichida to'lib qolishi ehtimoli.
- VM RAM usage doimiy 90% dan yuqori bo'lishi.

Dashboardda `Risklar` bo'limi chiqadi.

Har bir risk uchun:

- current value
- 7 kunlik average
- kunlik trend
- 7 kunlik forecast
- limitgacha taxminiy kun
- confidence
- tavsiya

Tavsiyalar:

- `RAM oshirish`
- `CPU limit tekshirish`
- `datastore kengaytirish`
- `VMni boshqa ESXi hostga ko'chirish`

Endpoint:

```text
GET /api/metrics/risks
```

## Asosiy API endpointlar

Auth:

```text
GET /api/auth/captcha
POST /api/auth/login
GET /api/auth/me
```

Metrics:

```text
GET /api/metrics/current
GET /api/metrics/history?entity_type=host&entity_id=1&range=1h
GET /api/metrics/risks
```

Hostlar:

```text
GET /api/hosts
POST /api/hosts
PUT /api/hosts/{host_id}
DELETE /api/hosts/{host_id}
```

Admin:

```text
GET /api/admin/branches
POST /api/admin/branches
PUT /api/admin/branches/{branch_id}
GET /api/admin/thresholds
PUT /api/admin/thresholds/{metric}
GET /api/admin/vms
POST /api/admin/vms
PUT /api/admin/vms/{vm_id}
PUT /api/admin/vms/{vm_id}/monitoring
DELETE /api/admin/vms/{vm_id}
GET /api/admin/notification-settings
PUT /api/admin/notification-settings
GET /api/admin/users
POST /api/admin/users
PUT /api/admin/users/{user_id}
GET /api/admin/logs
PUT /api/admin/logs/{log_id}
```

WebSocket:

```text
ws://localhost:3000/ws/metrics?token=<JWT>
```

Nginx frontend container bu so'rovni backenddagi `/ws/metrics` ga proxy qiladi.

## Admin panel

Admin quyidagilarni boshqaradi:

- Filial qo'shish va tahrirlash (`superadmin`).
- ESXi host qo'shish, tahrirlash, o'chirish.
- VM qo'shish, tahrirlash va o'chirish.
- VM monitoringni yoqish/o'chirish.
- Threshold sozlash.
- Telegram bot token va chat ID sozlash.
- Email SMTP sozlash.
- Foydalanuvchi qo'shish.
- Role berish: `superadmin`, `admin`, `kuzatuvchi`.
- Foydalanuvchini filialga biriktirish.
- Foydalanuvchini active/disabled qilish.
- Log jurnallarni ko'rish.
- Log yozuvlari statusi va admin izohini tahrirlash.

Role scope:

- `superadmin`: barcha filiallar, ESXi hostlar, VMlar, foydalanuvchilar, loglar va alertlar ustidan nazorat qiladi.
- `admin`: faqat o'z filialidagi host/VM monitoringi, foydalanuvchilar, loglar va sozlamalarni boshqaradi.
- `kuzatuvchi`: faqat o'z filialidagi dashboard, alert, risk va monitoring ma'lumotlarini ko'radi.
- Eski `viewer` role bootstrap vaqtida `kuzatuvchi` ga almashtiriladi.

## Log jurnallar

Admin paneldagi `Log jurnallar` menyusida tizim hodisalari va xatoliklar ko'rinadi.

Yozuv maydonlari:

- level: `info`, `warning`, `error`, `critical`
- category: `esxi`, `network`, `predictive`, va boshqa tizim kategoriyalari
- source: host/IP/worker nomi
- message
- details JSON
- status: `open`, `reviewed`, `resolved`
- admin note

`admin` o'z filiali log yozuvlarini, `superadmin` esa barcha filial log yozuvlarini tahrirlay oladi.

## Deploy

Linux serverga deploy qilish:

1. Docker va Docker Compose plugin o'rnating.
2. `monitoring-system` papkasini serverga ko'chiring.
3. `.env.example` dan `.env` yarating.
4. `SECRET_KEY`, `ADMIN_PASSWORD`, `POSTGRES_PASSWORD`, Telegram va SMTP qiymatlarini sozlang.
5. Firewall portlarini oching:
   - `3000` - frontend
   - `8000` - backend API, agar tashqaridan API kerak bo'lsa
6. Ishga tushiring:

```bash
docker compose up -d --build
```

7. Holatni tekshiring:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f worker
```

Productionda PostgreSQL volume uchun backup siyosatini alohida sozlang.

Linux serverda tez deploy:

```bash
chmod +x deploy-linux.sh
./deploy-linux.sh
```

Skript `.env` yo'q bo'lsa `.env.production.example` asosida yaratadi, `openssl` bor bo'lsa `SECRET_KEY`, `POSTGRES_PASSWORD` va `ADMIN_PASSWORD` ni avtomatik generatsiya qiladi, compose konfiguratsiyani tekshiradi, containerlarni build qilib ishga tushiradi va login ma'lumotlarini chiqaradi.

Server firewall uchun minimal portlar:

```bash
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
```

PostgreSQL va Redis tashqi tarmoqqa ochilmaydi; compose ularni faqat `127.0.0.1` ga bind qiladi.

## Troubleshooting

Docker Compose ishlamasa:

```bash
docker compose config
docker compose ps
docker compose logs backend
docker compose logs worker
```

Login ishlamasa:

- `.env` ichidagi `ADMIN_USERNAME` va `ADMIN_PASSWORD` ni tekshiring.
- Database birinchi marta yaratilganda admin user seed qilinadi.
- Eski volume bor bo'lsa, eski admin parol saqlangan bo'lishi mumkin.

ESXi ulanmasa:

- ESXi IP/hostname, username, password, portni tekshiring.
- ESXi management networkdan backend/worker konteyneri chiqishini tekshiring.
- SSL muammosi bo'lsa `verify_ssl=false` qilib ko'ring.
- Worker loglarini ko'ring: `docker compose logs -f worker`.

Ping ishlamasa:

- `worker` servisida `NET_RAW` capability berilgan.
- Firewall ICMP paketlarni bloklamaganini tekshiring.
- VM IP manzili ESXi guest tools orqali aniqlangan bo'lishi kerak.

WebSocket ulanmasa:

- Frontend http://localhost:3000 orqali ochilganini tekshiring.
- Nginx `/ws/` proxy sozlamasi bor.
- Browser devtools Network bo'limida `/ws/metrics` statusini tekshiring.

Frontend backendga ulanmasa:

- Frontend container ichida `/api` so'rovlari backendga proxy qilinadi.
- Direct Vite dev server ishlatsangiz `VITE_API_BASE_URL` va `VITE_WS_BASE_URL` sozlang.

## To'xtatish

Servislarni to'xtatish:

```bash
docker compose down
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\stop-real.ps1
```

Volume bilan birga tozalash:

```bash
docker compose down -v
```

`down -v` database va Redis ma'lumotlarini ham o'chiradi.
