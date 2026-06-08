# PixelGuard — Deployment Guide

## Prerequisites

- Docker + Docker Compose v2
- (or) Python 3.10+, Node 18+, and a MongoDB instance
- 4 GB RAM minimum for inference on CPU; 8 GB+ with an NVIDIA GPU for training
- A domain + TLS cert for production (Let's Encrypt via nginx/Caddy)

---

## Option A — Docker Compose (recommended for staging)

```bash
git clone <repo> pixelguard && cd pixelguard
git checkout tharushika/dev          # or main once merged
cp backend/.env.example backend/.env # tweak SECRET_KEY etc.

docker compose up -d --build
docker compose ps
```

Services:

| Container               | Port  | Purpose                          |
|-------------------------|-------|----------------------------------|
| `pixelguard-mongo`      | 27017 | MongoDB 7                        |
| `pixelguard-backend`    | 8000  | FastAPI + TensorFlow             |
| `pixelguard-frontend`   | 3000  | React (served via `serve`)       |
| `pixelguard-nginx` (opt)| 80/443| Reverse proxy (`--profile production`) |

Indexes are created automatically by the backend on startup. To force a re-create or wipe the DB:

```bash
docker compose exec backend python /app/../scripts/setup_db.py --drop
```

---

## Option B — Bare-metal / VM

### 1. MongoDB

Use MongoDB Atlas (managed) or self-host:

```bash
# Self-hosted (Ubuntu 22.04, replica-set ready for prod)
docker run -d --name mongo --restart unless-stopped \
  -v mongo_data:/data/db -p 27017:27017 mongo:7
```

For Atlas, grab the SRV connection string and set:

```env
MONGODB_URL=mongodb+srv://USER:PASS@cluster0.xxx.mongodb.net
MONGODB_DB=pixelguard
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Production: gunicorn with uvicorn workers
pip install gunicorn
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 60
```

For GPU inference, install `tensorflow[and-cuda]` instead of plain `tensorflow` and confirm with `python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"`.

### 3. Frontend

```bash
cd frontend
npm install
npm run build
# serve build/ via nginx, Cloudfront, Netlify, or `serve -s build -l 3000`
```

Set `REACT_APP_API_URL` to your public API hostname at build time.

---

## TLS & reverse proxy (nginx)

`docker-compose.yml` defines an `nginx` service under the `production` profile. Drop a config in `./nginx.conf` like:

```nginx
events {}
http {
  upstream backend  { server backend:8000;  }
  upstream frontend { server frontend:3000; }

  server {
    listen 80;
    server_name pixelguard.example.com;
    return 301 https://$host$request_uri;
  }
  server {
    listen 443 ssl http2;
    server_name pixelguard.example.com;
    ssl_certificate     /etc/letsencrypt/live/.../fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/.../privkey.pem;

    client_max_body_size 50M;       # match MAX_UPLOAD_SIZE
    location /api/    { proxy_pass http://backend; }
    location /docs    { proxy_pass http://backend; }
    location /health  { proxy_pass http://backend; }
    location /        { proxy_pass http://frontend; }
  }
}
```

Then:

```bash
docker compose --profile production up -d
```

---

## Environment variables (backend)

| Var                       | Default                            | Notes                                  |
|---------------------------|------------------------------------|----------------------------------------|
| `MONGODB_URL`             | `mongodb://localhost:27017`        | Connection string                      |
| `MONGODB_DB`              | `pixelguard`                       | DB name                                |
| `SECRET_KEY`              | `change-me-in-production`          | **Change in prod**                     |
| `ALLOWED_ORIGINS`         | localhost dev origins              | Comma-separated                        |
| `MAX_UPLOAD_SIZE`         | `52428800` (50 MB)                 | Match nginx `client_max_body_size`     |
| `UPLOAD_DIR`              | `./uploads`                        | Mount a persistent volume in prod      |
| `MODEL_PATH`              | `./models`                         | Where trained weights live             |
| `MESSAGE_LENGTH`          | `32`                               | Tracking-ID bit length                 |
| `IMAGE_SIZE`              | `256`                              | Inference input size                   |
| `DEBUG`                   | `False`                            | Enables auto-reload + verbose logs     |

---

## Smoke test

```bash
# Should print {"status":"healthy",...}
curl http://localhost:8000/health

# Encode a sample
curl -X POST http://localhost:8000/api/v1/encode/ \
  -F file=@sample.jpg \
  -F owner_name="Test User" \
  -F owner_email="test@example.com"

# Decode (use the encoded image you just got via /encode/download/{id})
curl -X POST http://localhost:8000/api/v1/decode/ -F file=@encoded.png
```

---

## Backups

- **MongoDB**: schedule daily `mongodump` to S3 / GCS.
  ```bash
  mongodump --uri="$MONGODB_URL" --db=pixelguard --archive=/backups/pixelguard-$(date +%F).archive
  ```
- **Uploads**: sync `./uploads/` to object storage (preferred: store directly to S3 instead of disk in prod — swap `ImageProcessor.save_image` for an S3 client).

---

## Production checklist

- [ ] Replace `SECRET_KEY` with a long random string
- [ ] Restrict `ALLOWED_ORIGINS` to your frontend domain
- [ ] Run behind HTTPS (nginx/Caddy/Cloudflare)
- [ ] Use managed MongoDB (Atlas) or a replica-set
- [ ] Mount `uploads/` to durable storage (or move to S3)
- [ ] Train the model on COCO 2017 — out-of-the-box weights are random init
- [ ] Set up monitoring (Prometheus + Grafana, or Datadog)
- [ ] Configure log aggregation (Loki / ELK)
- [ ] Add rate-limiting (nginx `limit_req` or FastAPI middleware)
