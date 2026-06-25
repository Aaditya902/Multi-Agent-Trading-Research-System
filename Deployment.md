# Deployment Guide

This guide covers three deployment options in order of complexity:

1. **Local (development)** — single machine, no Docker
2. **Docker Compose** — containerised, single server
3. **Production hardening** — checklist for going live

---

## Option 1 — Local Development

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10 or newer |
| pip | 23.0 or newer |
| RAM | 4 GB minimum (8 GB recommended for FinBERT) |
| Disk | 2 GB free (FinBERT model ~440 MB) |

### Step-by-step

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd indian_stock_platform

# 2. Create virtual environment
python -m venv .venv

# 3. Activate it
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\Activate.ps1      # Windows PowerShell

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
cp .env.example .env
# Open .env and set your GEMINI_API_KEY

# 6. Start the backend  (Terminal 1)
python app.py
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)

# 7. Start the frontend  (Terminal 2, same venv)
streamlit run frontend/app.py
# → http://localhost:8501
```

### Windows-specific notes

```powershell
# Use python instead of python3
python -m venv .venv
.venv\Scripts\Activate.ps1

# If execution policy blocks activation:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Kill stuck Python processes between restarts:
taskkill /IM python.exe /F
```

### Using Make

```bash
make setup      # one-time: creates venv, installs deps, copies .env
make run        # start backend
make frontend   # start frontend (separate terminal)
make test       # run tests
make clean      # remove caches
```

---

## Option 2 — Docker Compose

### Prerequisites

- Docker Engine 24.0+
- Docker Compose v2 (`docker compose`, not `docker-compose`)
- 4 GB RAM allocated to Docker
- `.env` file with `GEMINI_API_KEY` set

### Deploy

```bash
# 1. Copy and configure .env
cp .env.example .env
# Edit .env — set GEMINI_API_KEY

# 2. Build and start all services
make docker-up
# or directly:
docker compose up -d

# 3. Check health
docker compose ps
curl http://localhost:8000/health

# 4. View logs
make docker-logs
# or:
docker compose logs -f backend
docker compose logs -f frontend
```

### Service URLs

| Service | URL |
|---|---|
| FastAPI Backend | http://localhost:8000 |
| Swagger API Docs | http://localhost:8000/docs |
| Streamlit Frontend | http://localhost:8501 |

### Useful Docker commands

```bash
# Restart a single service
docker compose restart backend

# Stop all services
make docker-down

# Stop and remove all volumes (wipes database)
make docker-clean

# Rebuild after code changes
docker compose up -d --build

# Shell into the running backend container
docker exec -it stock_platform_backend bash

# Check resource usage
docker stats
```

### Docker volumes

| Volume | Contents |
|---|---|
| `stock_platform_db` | SQLite database (`stock_platform.db`) |
| `stock_platform_logs` | Application log files |
| `stock_platform_hf_cache` | FinBERT model cache (persists across restarts) |

---

## Option 3 — Production Hardening

### Environment variables

For production, set these additional variables:

```env
APP_ENV=production
LOG_LEVEL=INFO
GEMINI_MODEL=gemini-1.5-flash

# Use absolute path for DB to avoid working directory issues
DATABASE_URL=sqlite+aiosqlite:////app/data/stock_platform.db
```

### Reverse proxy with nginx

Place the FastAPI backend behind nginx for TLS termination and rate limiting.

**`/etc/nginx/sites-available/stock-platform`:**

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # FastAPI backend
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;    # analysis can take up to 2 minutes
        proxy_send_timeout 300s;
    }

    # Streamlit frontend
    location / {
        proxy_pass         http://127.0.0.1:8501;
        proxy_set_header   Host $host;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";  # WebSocket for Streamlit
        proxy_read_timeout 300s;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/stock-platform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Free TLS via Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Systemd service (non-Docker deployment)

**`/etc/systemd/system/stock-platform.service`:**

```ini
[Unit]
Description=Indian Stock Research Platform — FastAPI Backend
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/opt/indian_stock_platform
Environment=PATH=/opt/indian_stock_platform/.venv/bin
EnvironmentFile=/opt/indian_stock_platform/.env
ExecStart=/opt/indian_stock_platform/.venv/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable stock-platform
sudo systemctl start stock-platform
sudo systemctl status stock-platform

# View logs
sudo journalctl -u stock-platform -f
```

**`/etc/systemd/system/stock-platform-frontend.service`:**

```ini
[Unit]
Description=Indian Stock Research Platform — Streamlit Frontend
After=network.target stock-platform.service

[Service]
Type=simple
User=appuser
WorkingDirectory=/opt/indian_stock_platform
Environment=PATH=/opt/indian_stock_platform/.venv/bin
EnvironmentFile=/opt/indian_stock_platform/.env
ExecStart=/opt/indian_stock_platform/.venv/bin/streamlit run frontend/app.py \
    --server.port=8501 \
    --server.address=127.0.0.1 \
    --server.headless=true \
    --browser.gatherUsageStats=false
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Production security checklist

```
[ ] GEMINI_API_KEY stored as an environment secret (not committed to git)
[ ] .env is in .gitignore — never committed
[ ] APP_ENV=production (enables JSON logging, disables debug)
[ ] CORS origins tightened in app.py (replace "*" with your domain)
[ ] Nginx rate limiting enabled on /api/v1/analyze (prevents abuse)
[ ] SQLite DB file has correct permissions (chmod 600)
[ ] Log rotation configured (loguru handles this automatically)
[ ] Docker containers run as non-root user (already configured)
[ ] Health check endpoint monitored by uptime service
[ ] Gemini free-tier quota monitored in Google AI Studio
```

### Tightening CORS for production

In `app.py`, replace:

```python
# Development (wide open)
allow_origins=["*"],
```

With:

```python
# Production (locked to your domain)
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
],
```

### Gemini free-tier limits

| Limit | Value |
|---|---|
| Requests per minute | 15 |
| Requests per day | 1,500 |
| Tokens per minute | 1,000,000 |

Each `/analyze` call uses **1 Gemini call** (report generation).
Each `/compare` call uses **3 calls** (2 analyses + 1 comparison).

At 15 RPM, you can run approximately **5 stock analyses per minute** comfortably.

### Recommended server specs (cloud VM)

| Traffic | vCPU | RAM | Storage | Estimated Cost |
|---|---|---|---|---|
| Personal use | 1 | 4 GB | 20 GB | ~$5–10/month |
| Small team | 2 | 8 GB | 40 GB | ~$20–30/month |
| Production | 4 | 16 GB | 80 GB | ~$60–80/month |

Tested on: AWS t3.medium, GCP e2-medium, DigitalOcean 4GB Droplet, Hetzner CX21.

---

## Upgrading

```bash
# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Restart services
# Local:
# kill the running python app.py and restart
# Docker:
docker compose up -d --build

# Systemd:
sudo systemctl restart stock-platform
sudo systemctl restart stock-platform-frontend
```

---

## Backup

```bash
# Backup SQLite database (local)
cp stock_platform.db stock_platform_backup_$(date +%Y%m%d).db

# Backup Docker volume
docker run --rm \
    -v stock_platform_db:/data \
    -v $(pwd):/backup \
    alpine tar czf /backup/db_backup_$(date +%Y%m%d).tar.gz -C /data .
```