# PixelGuard — API reference

Interactive docs are available at:

- Swagger UI : `GET /docs`
- ReDoc      : `GET /redoc`

## Base URL

```
http://localhost:8000
```

All business endpoints live under `/api/v1/`.

---

## Meta

### `GET /health`

```json
{ "status": "healthy", "app": "PixelGuard", "version": "1.0.0" }
```

---

## Encode

### `POST /api/v1/encode/`

Embed a tracking ID into a cover image.

**Request** (`multipart/form-data`):

| Field         | Type   | Required | Notes                            |
|---------------|--------|----------|----------------------------------|
| `file`        | file   | yes      | jpg/jpeg/png/bmp/webp, ≤ 50 MB    |
| `owner_name`  | string | yes      | 1-200 chars                       |
| `owner_email` | string | yes      | email                             |
| `location`    | string | no       | up to 200 chars                   |
| `description` | string | no       | up to 2000 chars                  |

**Response 200**:

```json
{
  "tracking_id": "9f3a1c2b4d5e6789",
  "psnr": 42.31,
  "ssim": 0.9912,
  "encoded_image_url": "/api/v1/encode/download/9f3a1c2b4d5e6789",
  "download_url":      "/api/v1/encode/download/9f3a1c2b4d5e6789",
  "created_at": "2026-06-08T17:30:00Z",
  "owner_name": "Jane Doe",
  "owner_email": "jane@example.com"
}
```

### `GET /api/v1/encode/download/{tracking_id}`

Stream the stamped PNG. Returns `image/png`.

### `POST /api/v1/encode/test-robustness`

Encode then decode under several distortions; returns per-distortion accuracy.

---

## Decode

### `POST /api/v1/decode/`

Recover the tracking ID embedded in an uploaded image.

**Request** (`multipart/form-data`):

| Field  | Type | Required |
|--------|------|----------|
| `file` | file | yes      |

**Response 200**:

```json
{
  "tracking_id": "9f3a1c2b4d5e6789",
  "confidence":  92.4,
  "found":       true,
  "owner_name":  "Jane Doe",
  "owner_email": "jane@example.com",
  "location":    "Galle, Sri Lanka",
  "description": "Portfolio image #42",
  "created_at":  "2026-06-08T17:30:00Z"
}
```

If the decoded ID is not in our database:

```json
{ "tracking_id": "abc…", "confidence": 23.1, "found": false }
```

### `POST /api/v1/decode/with-distortion`

| Field             | Type   | Default |
|-------------------|--------|---------|
| `file`            | file   | —       |
| `distortion_type` | string | `jpeg`  |

Available distortions: `identity`, `jpeg`, `blur`, `crop`, `resize`.

---

## Tracking

### `GET /api/v1/tracking/{tracking_id}`

```json
{
  "tracking_id": "9f3a1c2b4d5e6789",
  "owner_name":  "Jane Doe",
  "owner_email": "jane@example.com",
  "location":    "Galle, Sri Lanka",
  "description": "Portfolio image #42",
  "created_at":  "2026-06-08T17:30:00Z",
  "is_active":   true
}
```

`404` if the tracking ID doesn't exist or has been soft-deleted.

### `GET /api/v1/tracking/user/{user_id}/tracking-ids?skip=0&limit=100`

List a user's tracking IDs, newest first.

### `GET /api/v1/tracking/user/{user_id}/statistics`

```json
{
  "tracking_ids":         12,
  "encoded_images":       12,
  "decoding_attempts":    47,
  "successful_decodings": 41,
  "success_rate":         87.23
}
```

### `DELETE /api/v1/tracking/{tracking_id}`

Soft-delete (sets `is_active=false`). Returns the deactivated record.

---

## Error responses

All errors use the same envelope:

```json
{ "detail": "Human-readable explanation" }
```

| Status | Meaning                                            |
|--------|----------------------------------------------------|
| 400    | Bad input (empty upload, unreadable image, …)       |
| 404    | Tracking ID not found                              |
| 413    | Upload exceeds `MAX_UPLOAD_SIZE`                   |
| 415    | Unsupported file extension                          |
| 500    | Internal error (DB write failed, model crashed)    |
