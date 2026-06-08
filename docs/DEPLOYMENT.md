# PixelGuard — Deployment Guide

PixelGuard runs as three independent pieces: a MongoDB database, a FastAPI backend, and a React frontend. You can host each one anywhere — managed services keep things simplest.

## Recommended production stack

| Component       | Where to host                       | Cost (dev/demo) |
|-----------------|-------------------------------------|-----------------|
| Database        | **MongoDB Atlas** (free M0 cluster) | $0              |
| Backend         | **Render** or **Railway** or **Fly.io** | free tier OK  |
| Frontend        | **Vercel** or **Netlify**           | free            |
| Trained weights | Commit to repo, or push to **Hugging Face Hub** / S3 | $0           |

This setup needs no Docker, no VM management, and no manual TLS — every service handles its own runtime.

---

## 1. MongoDB Atlas

1. Sign up at <https://www.mongodb.com/cloud/atlas> and create an **M0** (free) cluster.
2. Database Access → add a user with read/write on `pixelguard`.
3. Network Access → allow `0.0.0.0/0` for the demo (or your backend's egress IP in prod).
4. Connect → copy the SRV URL:
   ```
   mongodb+srv://USER:PASS@cluster0.xxx.mongodb.net
   ```
5. Set this as `MONGODB_URL` in your backend environment.

The first time the backend starts against a fresh DB, `ensure_indexes()` creates every index it needs.

---

## 2. Backend on Render (example)

Render auto-detects the FastAPI app from `backend/`.

1. New Web Service → connect your repo → root `backend/`.
2. Build command:
   ```
   pip install -r requirements.txt
   ```
3. Start command:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Environment variables (Settings → Environment):

   | Var                | Value                                          |
   |--------------------|------------------------------------------------|
   | `MONGODB_URL`      | (Atlas SRV URL)                                |
   | `MONGODB_DB`       | `pixelguard`                                   |
   | `SECRET_KEY`       | long random string                             |
   | `ALLOWED_ORIGINS`  | `https://your-frontend.vercel.app`             |
   | `DEBUG`            | `False`                                        |

5. Use a paid plan (or persistent disk) if you want `./uploads` to survive restarts. **Better long-term**: swap the disk write in `app/routes/encode.py` for an S3 upload (the path field in MongoDB then stores the S3 URL).

Railway and Fly.io work the same way — point at `backend/`, set env vars, deploy.

### Production process settings

For more throughput:

```bash
pip install gunicorn
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:$PORT \
  --timeout 60
```

TensorFlow inference is CPU-bound; 4 workers on a 2 vCPU instance is usually a sweet spot.

For GPU inference (much faster encoding), use a GPU host (Modal, Banana, RunPod) and install `tensorflow[and-cuda]` instead of plain `tensorflow`.

---

## 3. Frontend on Vercel (example)

1. Import the GitHub repo into Vercel.
2. Root directory: `frontend/`.
3. Framework preset: Create React App.
4. Environment variable:
   ```
   REACT_APP_API_URL = https://your-backend.onrender.com
   ```
5. Deploy. Vercel auto-builds on every push.

Netlify works identically (build command `npm run build`, publish dir `build/`).

---

## 4. Self-hosted on a single VM (Ubuntu 22.04)

If you'd rather run everything on one box (a $5 droplet for the demo):

```bash
# --- prereqs ---
sudo apt update
sudo apt install -y python3.10 python3.10-venv nodejs npm nginx mongodb

# --- pull the repo ---
git clone <repo> /opt/pixelguard && cd /opt/pixelguard
git checkout tharushika/dev

# --- backend ---
cd backend
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt gunicorn
cp .env.example .env       # edit MONGODB_URL=mongodb://localhost:27017

# Run as a systemd service (see /etc/systemd/system/pixelguard.service below)
sudo systemctl enable --now pixelguard
sudo systemctl enable --now mongod

# --- frontend ---
cd ../frontend
npm install
npm run build              # produces build/
# Then point nginx at build/ (see nginx config below)
```

### `/etc/systemd/system/pixelguard.service`

```ini
[Unit]
Description=PixelGuard FastAPI backend
After=network.target mongod.service

[Service]
WorkingDirectory=/opt/pixelguard/backend
EnvironmentFile=/opt/pixelguard/backend/.env
ExecStart=/opt/pixelguard/backend/.venv/bin/gunicorn \
  app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

### `/etc/nginx/sites-available/pixelguard`

```nginx
server {
  listen 80;
  server_name pixelguard.example.com;

  client_max_body_size 50M;

  # Frontend static build
  root /opt/pixelguard/frontend/build;
  index index.html;
  location / {
    try_files $uri /index.html;
  }

  # Backend API
  location /api/   { proxy_pass http://127.0.0.1:8000; }
  location /docs   { proxy_pass http://127.0.0.1:8000; }
  location /health { proxy_pass http://127.0.0.1:8000; }
}
```

Add TLS with Certbot:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d pixelguard.example.com
```

---

## Environment variables (backend)

| Var                       | Default                            | Notes                                  |
|---------------------------|------------------------------------|----------------------------------------|
| `MONGODB_URL`             | `mongodb://localhost:27017`        | Connection string                      |
| `MONGODB_DB`              | `pixelguard`                       | DB name                                |
| `SECRET_KEY`              | `change-me-in-production`          | **Change in prod**                     |
| `ALLOWED_ORIGINS`         | localhost dev origins              | Comma-separated list                   |
| `MAX_UPLOAD_SIZE`         | `52428800` (50 MB)                 | Match nginx `client_max_body_size`     |
| `UPLOAD_DIR`              | `./uploads`                        | Persistent disk path, or `/tmp` if S3  |
| `MODEL_PATH`              | `./models`                         | Where trained weights live             |
| `MESSAGE_LENGTH`          | `32`                               | Tracking-ID bit length                 |
| `IMAGE_SIZE`              | `256`                              | Inference input size                   |
| `DEBUG`                   | `False`                            | Enables auto-reload + verbose logs     |

---

## Smoke test

```bash
# Should print {"status":"healthy",...}
curl https://your-backend.example.com/health

# Encode
curl -X POST https://your-backend.example.com/api/v1/encode/ \
  -F file=@sample.jpg \
  -F owner_name="Test User" \
  -F owner_email="test@example.com"

# Decode (use the file you downloaded from /encode/download/{id})
curl -X POST https://your-backend.example.com/api/v1/decode/ -F file=@encoded.png
```

---

## Backups

- **MongoDB**: Atlas does this for you (continuous backup on M10+, daily snapshots on M0). Self-hosted: schedule daily `mongodump` to S3.
- **Uploads**: if you keep them on disk, sync to object storage with `rclone`. Better: skip the disk entirely and upload directly to S3 from the encode route.

---

## Production checklist

- [ ] Replace `SECRET_KEY` with a long random string
- [ ] Restrict `ALLOWED_ORIGINS` to your frontend domain
- [ ] Use Atlas (or a replica-set self-host) rather than a single Mongo node
- [ ] Move `uploads/` to S3 / R2 / GCS for durability
- [ ] Train the model on COCO 2017 — shipped weights are random init
- [ ] Set up monitoring (UptimeRobot for free, or Datadog / Grafana Cloud)
- [ ] Add rate-limiting (nginx `limit_req` or a FastAPI middleware)
- [ ] Run the backend behind HTTPS (Render/Vercel give this free; nginx + Certbot for self-host)
