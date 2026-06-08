# PixelGuard — Project Structure

```
PixelGuard/
├── README.md                        Quick start + overview
├── PROJECT_STRUCTURE.md             This file
├── .env                             Local dev defaults (gitignored)
├── .gitignore
│
├── backend/                         FastAPI + TensorFlow + MongoDB
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── __init__.py
│       ├── main.py                  FastAPI app, lifespan, CORS, router wiring
│       ├── config.py                Pydantic settings (env-driven)
│       │
│       ├── database/
│       │   ├── __init__.py          Re-exports Motor helpers
│       │   ├── database.py          Async MongoDB client + ensure_indexes()
│       │   └── schemas.py           Pydantic request/response + doc shapes
│       │
│       ├── models/                  TensorFlow networks
│       │   ├── encoder.py           FCN encoder with 1×1 fuse + residual blocks
│       │   ├── decoder.py           GAP-based decoder (crop/resize robust)
│       │   ├── discriminator.py     Binary classifier (adversarial loss)
│       │   └── noise_layer.py       Differentiable distortions for training
│       │
│       ├── services/
│       │   ├── steganography_service.py    encode() / decode() / test_robustness()
│       │   └── tracking_service.py         Async MongoDB CRUD
│       │
│       ├── routes/
│       │   ├── encode.py            POST /encode/, GET /download/{id}, /test-robustness
│       │   ├── decode.py            POST /decode/, /decode/with-distortion
│       │   └── tracking.py          GET /{id}, list, statistics, DELETE soft-delete
│       │
│       └── utils/
│           ├── image_utils.py       OpenCV/PIL I/O, YCbCr conversion, hashing
│           ├── metrics.py           PSNR, SSIM, bit accuracy, BER
│           └── noise_utils.py       NumPy-side distortion helpers
│
├── frontend/                        React 18 SPA
│   ├── package.json
│   ├── public/index.html
│   └── src/
│       ├── index.js
│       ├── App.jsx                  Routes
│       ├── pages/
│       │   ├── Home.jsx             Landing / marketing
│       │   ├── Encode.jsx           Upload + metadata form
│       │   ├── Decode.jsx           Upload + result panel
│       │   └── About.jsx
│       ├── components/
│       │   ├── Header.jsx
│       │   ├── Footer.jsx
│       │   ├── Navigation.jsx
│       │   └── LoadingSpinner.jsx
│       ├── services/
│       │   ├── api.js               Axios client + endpoint wrappers
│       │   └── auth.js              (Reserved — auth not wired yet)
│       └── styles/
│           ├── globals.css
│           ├── variables.css
│           └── components.css
│
├── scripts/
│   ├── train_model.py               TensorFlow training loop
│   ├── setup_db.py                  Bootstrap MongoDB indexes (idempotent; --drop to wipe)
│   ├── start.sh                     Dev startup, macOS / Linux
│   └── start.ps1                    Dev startup, Windows PowerShell
│
└── docs/
    ├── ARCHITECTURE.md              System design, MongoDB schema, training loop
    ├── API.md                       Endpoint reference (Swagger lives at /docs)
    ├── DEPLOYMENT.md                Atlas + Render/Vercel + self-host VM recipes
    └── USER_GUIDE.md                End-user instructions
```

## Stack

| Layer       | Tech                                              |
|-------------|---------------------------------------------------|
| Frontend    | React 18, react-router, react-dropzone, axios     |
| Backend     | FastAPI 0.110, Uvicorn, Motor 3.4 (async Mongo)   |
| Database    | MongoDB 7 (local install or Atlas)                |
| ML / CV     | TensorFlow 2.15, OpenCV, Kornia, scikit-image     |
| Auth        | JWT (scaffolded, not yet wired)                   |

## MongoDB collections

| Collection         | Key field        | Purpose                                          |
|--------------------|------------------|--------------------------------------------------|
| `tracking_ids`     | `tracking_id`    | Per-image owner metadata (lookup table)          |
| `encoded_images`   | `tracking_id`    | One row per generated stego image (paths, PSNR)  |
| `decoding_logs`    | `tracking_id`    | Audit trail of decode attempts                   |
| `users`            | `email`          | Reserved for future authentication               |

All indexes are created idempotently at backend startup.

## Implementation status

| Area                                 | Status                                                |
|--------------------------------------|-------------------------------------------------------|
| Encoder / Decoder / Discriminator    | Implemented (random init out of the box)              |
| Differentiable noise layer           | identity, crop, resize, blur, dropout, JPEG approx    |
| `/encode` + persistence              | Done                                                  |
| `/decode` + metadata lookup          | Done                                                  |
| `/encode/download/{id}`              | Done                                                  |
| Tracking ID CRUD + soft-delete       | Done                                                  |
| User-stats aggregation               | Done                                                  |
| React UI for encode + decode         | Done                                                  |
| Authentication wired into routes     | Scaffolded only                                        |
| Real training on COCO 2017           | Training script ready — runs pending                  |
| Deployment recipes                   | See `docs/DEPLOYMENT.md` (Atlas + Render/Vercel)      |
