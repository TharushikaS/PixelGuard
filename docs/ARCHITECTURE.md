# PixelGuard — Architecture

## System overview

PixelGuard is a SaaS for embedding (and later recovering) a unique tracking ID inside an image using deep-learning steganography. The stack:

```
┌────────────┐       multipart       ┌──────────────────┐      Motor       ┌──────────┐
│  React UI  │ ───── upload ──────▶ │  FastAPI (REST)  │ ───── async ──▶ │ MongoDB  │
└────────────┘                       │  - /encode       │                  └──────────┘
       ▲                             │  - /decode       │
       │  stamped PNG + tracking ID  │  - /tracking     │
       │ ◀────────────────────────── │  - /download/:id │
                                     └────────┬─────────┘
                                              │  TensorFlow
                                              ▼
                                  ┌────────────────────────────┐
                                  │  Encoder → NoiseLayer →    │
                                  │  Decoder + Discriminator   │
                                  └────────────────────────────┘
```

## Component map

| Layer        | Modules                                                                  |
|--------------|--------------------------------------------------------------------------|
| Routes       | `app/routes/encode.py`, `decode.py`, `tracking.py`                       |
| Services     | `app/services/steganography_service.py`, `tracking_service.py`           |
| Models (ML)  | `app/models/encoder.py`, `decoder.py`, `discriminator.py`, `noise_layer.py` |
| Utils        | `app/utils/image_utils.py`, `metrics.py`, `noise_utils.py`               |
| Persistence  | `app/database/database.py` (Motor client), `schemas.py` (Pydantic)       |

## Network architectures

### Encoder (fully-convolutional, resolution-agnostic)

```
Cover Image (H×W×3) ─┐
                     ├─ Conv 64 → Conv 128         (image features)
Message (L,) ────────┤
                     ├─ Dense → reshape → tile      (spatial message volume)
                     ▼
                Concat → 1×1 Proj → 128ch
                     │
                Residual × 4 (128ch each)
                     │
                Conv 3 + Sigmoid → Stego Image (H×W×3)
```

### Decoder (GAP-based, robust to crop / resize)

```
Stego Image ─▶ Conv→Pool→Conv→Pool→Conv → Conv(L) → GAP → Dense → Sigmoid
                                                          ▲
                                            spatial dims collapse here
```

### Discriminator (binary classifier — drives adversarial loss)

```
Image ─▶ Conv blocks ─▶ GAP ─▶ Dense ─▶ Sigmoid ─▶ P(stego)
```

### Noise layer (training-time only)

Random per-batch selection from: identity, crop, resize, Gaussian blur, pixel dropout, JPEG approximation (DCT-domain quantization).

## Data flow

### Encode

```
upload ─▶ ImageProcessor.load_image_from_bytes
       ─▶ SteganographyService.generate_tracking_id   (uuid4[:16])
       ─▶ TrackingService.create_tracking_id         (MongoDB write #1)
       ─▶ Encoder.forward → stego image
       ─▶ MetricsCalculator.psnr / .ssim
       ─▶ save PNG to UPLOAD_DIR
       ─▶ TrackingService.log_encoded_image           (MongoDB write #2)
       ─▶ return tracking_id + metrics + download URL
```

### Decode

```
upload ─▶ ImageProcessor.load_image_from_bytes
       ─▶ Decoder.forward → predicted bits
       ─▶ binary_to_message → tracking_id
       ─▶ TrackingService.get_tracking_id            (MongoDB read)
       ─▶ TrackingService.log_decoding_attempt        (MongoDB write)
       ─▶ return metadata (or found=false)
```

## MongoDB schema

PixelGuard uses 4 collections. All `_id` fields are auto-generated `ObjectId`; we add our own stable string IDs for cross-collection joins.

### `tracking_ids`

```jsonc
{
  "tracking_id": "9f3a1c2b4d5e6789",   // unique, app-generated
  "user_id":     "u_abc123" | null,
  "owner_name":  "Jane Doe",
  "owner_email": "jane@example.com",
  "location":    "Galle, Sri Lanka",
  "description": "Portfolio image #42",
  "original_filename": "sunset.jpg",
  "is_active":   true,
  "created_at":  ISODate,
  "updated_at":  ISODate
}
```

Indexes:
- `{tracking_id: 1}` unique
- `{user_id: 1, created_at: -1}`
- `{owner_email: 1}`

### `encoded_images`

```jsonc
{
  "id":           "uuid4",
  "tracking_id":  "9f3a1c2b4d5e6789",
  "user_id":      "u_abc123" | null,
  "encoded_path": "/app/uploads/9f3a1c2b4d5e6789.png",
  "original_filename": "sunset.jpg",
  "image_hash":   "sha256:…",
  "psnr":         42.7,
  "ssim":         0.9912,
  "file_size":    301245,
  "created_at":   ISODate
}
```

Indexes:
- `{tracking_id: 1}`
- `{image_hash: 1}` unique sparse

### `decoding_logs`

```jsonc
{
  "id":          "uuid4",
  "tracking_id": "9f3a1c2b4d5e6789",
  "decoded_id":  "9f3a1c2b4d5e6789",
  "success":     true,
  "confidence":  92.4,
  "created_at":  ISODate
}
```

Indexes:
- `{tracking_id: 1, created_at: -1}`

### `users` (reserved for auth)

```jsonc
{
  "id": "u_abc123",
  "username": "jane",
  "email": "jane@example.com",
  "hashed_password": "$2b$…",
  "is_active": true,
  "created_at": ISODate,
  "updated_at": ISODate
}
```

Indexes:
- `{email: 1}` unique

All indexes are created idempotently on app startup via `ensure_indexes()` in `database/database.py`.

## Training loop

```
for epoch in epochs:
  cover, msg ← sample batch
  enc       = Encoder(cover, msg)
  noisy_enc = NoiseLayer(enc)             # random distortion per batch
  pred_msg  = Decoder(noisy_enc)

  L_recon   = MSE(cover, enc)
  L_msg     = BCE(msg, pred_msg)
  L_adv     = BCE(0, Discriminator(enc))   # fool D
  L_total   = L_recon + L_msg + 0.001·L_adv

  step Encoder, Decoder
  step Discriminator with BCE(real=1, fake=0)
```

See `scripts/train_model.py`.

## Performance & scaling notes

- **GPU**: TensorFlow auto-detects CUDA; falls back to CPU.
- **Caching**: encoder/decoder graphs are built once per process; reuse across requests.
- **Async I/O**: Motor + FastAPI async means file uploads and DB writes do not block the event loop.
- **Mongo scaling**: tracking-ID reads are point lookups on an indexed unique field — sub-ms. Decoding logs can grow unbounded; add a TTL index in production if storage is a concern.
- **Stateless backend**: scale horizontally behind a load balancer; share `./uploads` via S3 or a network volume.
