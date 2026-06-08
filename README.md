# PixelGuard

> Hide a tracking ID inside image pixels with a **robust deep-learning steganography algorithm**, expose it as a SaaS, and trace ownership of images shared on social media.

PixelGuard is built around an end-to-end neural watermarking pipeline (HiDDeN-style encoder + GAP-based decoder + discriminator), wrapped in a FastAPI service backed by MongoDB and served through a React frontend. Robustness against JPEG compression, blur, cropping, and resizing is baked into the noise layer during training.

---

## Table of contents

1. [Architecture](#architecture)
2. [Tech stack](#tech-stack)
3. [Repository layout](#repository-layout)
4. [Prerequisites](#prerequisites)
5. [Quick start](#quick-start)
6. [API overview](#api-overview)
7. [Training the model](#training-the-model)
8. [Deployment](#deployment)

---

## Architecture

```
┌────────────┐       multipart       ┌──────────────────┐      Motor       ┌──────────┐
│  React UI  │ ───── upload ──────▶ │  FastAPI (REST)  │ ───── async ──▶ │ MongoDB  │
└────────────┘                       │  - /encode       │                  └──────────┘
       ▲                             │  - /decode       │
       │   stamped PNG + tracking ID │  - /tracking     │
       │ ◀────────────────────────── │  - /download/:id │
                                     └────────┬─────────┘
                                              │  TensorFlow
                                              ▼
                                  ┌────────────────────────────┐
                                  │  Encoder → NoiseLayer →    │
                                  │  Decoder + Discriminator   │
                                  └────────────────────────────┘
```

The encoder is a fully-convolutional network: it tiles the binary tracking ID into a spatial feature volume, concatenates it with image features, fuses with a 1×1 projection, and passes the result through residual blocks. The decoder collapses spatial dimensions with global average pooling so it is robust to crops and resizes.

## Tech stack

| Layer       | Tech                                       |
|-------------|--------------------------------------------|
| Frontend    | React 18 (CRA), react-router, react-dropzone, axios |
| Backend     | FastAPI 0.110, Uvicorn, Motor 3.4 (async Mongo) |
| Database    | MongoDB 7 (local install **or** MongoDB Atlas) |
| ML / CV     | TensorFlow 2.15, OpenCV (headless), Kornia, scikit-image |

## Repository layout

```
PixelGuard/
├── backend/                  FastAPI service
│   ├── app/
│   │   ├── main.py           App factory + lifespan
│   │   ├── config.py         Pydantic settings (env-driven)
│   │   ├── database/
│   │   │   ├── database.py   Motor client + index management
│   │   │   └── schemas.py    Pydantic request/response + doc shapes
│   │   ├── models/           Encoder / Decoder / Discriminator / NoiseLayer
│   │   ├── services/         SteganographyService, TrackingService (Mongo CRUD)
│   │   ├── routes/           /encode, /decode, /tracking
│   │   └── utils/            Image I/O, metrics, noise helpers
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                 React SPA
│   ├── src/
│   │   ├── pages/            Home, Encode, Decode, About
│   │   ├── components/       Header, Footer, LoadingSpinner, Navigation
│   │   ├── services/api.js   Axios client
│   │   └── styles/           CSS (globals, components, variables)
│   └── package.json
│
├── scripts/
│   ├── train_model.py        TensorFlow training loop
│   ├── setup_db.py           MongoDB index bootstrap
│   ├── start.sh              One-shot dev startup (macOS / Linux)
│   └── start.ps1             One-shot dev startup (Windows PowerShell)
│
├── docs/                     Architecture, API, Deployment, User guide
├── .env                      Local-dev env defaults
└── README.md
```

## Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **MongoDB** — choose one:
  - Install **MongoDB Community Server** locally (Windows installer, `brew install mongodb-community` on macOS, or apt on Linux). It listens on `27017` by default.
  - **OR** use **MongoDB Atlas** (free tier) — sign up at mongodb.com/cloud/atlas, create an M0 cluster, copy the SRV connection string, and put it in `backend/.env`.

That's it — no Docker, no virtualization.

## Quick start

### Option 1: scripted (recommended)

```bash
# macOS / Linux
bash scripts/start.sh

# Windows (PowerShell)
pwsh scripts\start.ps1
```

These create the Python venv, install dependencies, ensure Mongo indexes, and launch both servers.

### Option 2: manual, three terminals

**Terminal 1 — MongoDB** (skip if using Atlas)

```bash
# macOS:   brew services start mongodb-community
# Linux:   sudo systemctl start mongod
# Windows: services.msc → MongoDB Server → Start  (auto-starts on install)
```

**Terminal 2 — Backend**

```bash
cd backend
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env          # then edit MONGODB_URL if using Atlas

python ../scripts/setup_db.py  # one-time: create Mongo indexes
uvicorn app.main:app --reload --port 8000
```

**Terminal 3 — Frontend**

```bash
cd frontend
npm install
npm start                      # opens http://localhost:3000
```

Then visit:
- UI    → http://localhost:3000
- API   → http://localhost:8000
- Docs  → http://localhost:8000/docs

## API overview

| Method | Path                                       | Purpose                                                   |
|--------|--------------------------------------------|-----------------------------------------------------------|
| GET    | `/health`                                  | Liveness probe                                            |
| POST   | `/api/v1/encode/`                          | Upload cover image + metadata → returns tracking ID + PSNR/SSIM + download URL |
| GET    | `/api/v1/encode/download/{tracking_id}`    | Stream the stamped PNG                                    |
| POST   | `/api/v1/encode/test-robustness`           | Run a per-distortion bit-accuracy report                  |
| POST   | `/api/v1/decode/`                          | Upload any image → recover ID + metadata if known         |
| POST   | `/api/v1/decode/with-distortion`           | Apply distortion in-flight then decode (demo)             |
| GET    | `/api/v1/tracking/{tracking_id}`           | Lookup metadata                                           |
| GET    | `/api/v1/tracking/user/{uid}/tracking-ids` | List a user's IDs                                         |
| GET    | `/api/v1/tracking/user/{uid}/statistics`   | Aggregate stats                                           |
| DELETE | `/api/v1/tracking/{tracking_id}`           | Soft-delete                                               |

Full schemas and examples: `/docs` (Swagger UI) or `/redoc`.

## Training the model

```bash
# Default: 10 epochs on synthetic data — for smoke testing only.
python scripts/train_model.py --epochs 50 --batch-size 16 --model-path ./models
```

For real performance, plug COCO 2017 into `scripts/train_model.py` (see the docstring inside) and train for ≥ 200 epochs as in the original HiDDeN paper.

## Deployment

For production hosting, see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — recommended stack:

- **Database** → MongoDB Atlas (managed, free tier covers a demo)
- **Backend**  → Render / Railway / Fly.io (any Python-friendly PaaS)
- **Frontend** → Vercel / Netlify (CRA static build)

---

**Project**: EE7204 / EC7205 — Image Processing and Computer Vision, University of Ruhuna
**Team**: M.A.P. Imalsha, A.R.M.D.D. Kumara, W.G.I.S. Madusanka, R.L.D.T.H. Surasinghe
