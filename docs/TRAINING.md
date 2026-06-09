# PixelGuard — Training Guide

This guide walks you from zero → trained HiDDeN-style watermarker → swapped
into your SaaS. The recommended path uses **Google Colab's free T4 GPU**.
A local GPU works identically; CPU works but takes 100× longer (skip it).

---

## Recipe at a glance

| Item                         | Value                                                  |
|------------------------------|--------------------------------------------------------|
| Architecture                 | HiDDeN (encoder + decoder + discriminator + noise layer)|
| Image size                   | 128 × 128 (paper default)                              |
| Message length               | 32 bits                                                |
| Dataset                      | COCO 2017 train, or a 10k–20k subset                   |
| Batch size                   | 12                                                     |
| Optimizer                    | Adam, lr = 1e-3                                        |
| Loss weights (proposal)      | λ_I = 0.7 (image), λ_G = 0.001 (adversarial)           |
| Noise curriculum             | Combined: random distortion per minibatch              |
| Epochs                       | 200 (full), 50–80 (quick demo)                         |
| Wall-clock on a T4 GPU       | ~6 h full, ~90 min demo                                |

---

## Step 1 — Open a Colab notebook with GPU

1. Go to https://colab.research.google.com → **New Notebook**.
2. In the top menu: **Runtime → Change runtime type → T4 GPU → Save**.
3. Verify the GPU is attached:
   ```python
   !nvidia-smi
   ```
   You should see a `Tesla T4` row with ~15 GB memory free.

> Free Colab gives ~12 h of GPU per day. If you run out, switch Google
> accounts or come back tomorrow. Kaggle Notebooks is a free alternative
> with ~30 GPU-hours/week.

---

## Step 2 — Pull the code into Colab

In a new cell:

```python
# Option A: clone from GitHub (after you push the repo)
!git clone <your-repo-url>
%cd PixelGuard

# Option B: upload the backend/ + scripts/ folders manually
# (use the left sidebar's "Files" tab → "Upload")
```

Make sure you end up with this structure inside Colab:

```
PixelGuard/
├── backend/app/models/  ← needed
├── scripts/train_model.py
└── (other files don't matter for training)
```

---

## Step 3 — Install dependencies

Colab already has TensorFlow, NumPy and Pillow pre-installed. Sanity check:

```python
import tensorflow as tf, sys
print("TF:", tf.__version__)
print("Python:", sys.version)
print("GPU devices:", tf.config.list_physical_devices("GPU"))
```

You want **TF ≥ 2.10** and at least one GPU listed. If TF is older:

```python
!pip install -q "tensorflow==2.15.0"
```

(Then **Runtime → Restart runtime** — you must restart after a TF upgrade.)

---

## Step 4 — Get training images

Three options, fastest to slowest:

### Option A — Tiny smoke-test dataset (1 min, ~100 MB)

For verifying the script runs end-to-end:

```python
!pip install -q tensorflow-datasets
import tensorflow_datasets as tfds, os, pathlib
ds = tfds.load("tf_flowers", split="train", as_supervised=False)

out = pathlib.Path("/content/tiny_images")
out.mkdir(exist_ok=True)
for i, ex in enumerate(ds.take(2000)):
    tf.io.write_file(
        str(out / f"{i:05d}.jpg"),
        tf.io.encode_jpeg(tf.cast(ex["image"], tf.uint8))
    )
print("Wrote", len(list(out.iterdir())), "images")
```

### Option B — COCO 2017 subset (~5 min, 1–2 GB)

A 10k-image subset is plenty for a good demo:

```python
import os, urllib.request, zipfile, random, shutil

# COCO 2017 train images (18 GB full — we'll only keep 10k)
!wget -q http://images.cocodataset.org/zips/train2017.zip
!unzip -q train2017.zip
files = os.listdir("train2017")
random.seed(42)
keep = random.sample(files, 10000)
os.makedirs("coco_subset", exist_ok=True)
for f in keep:
    shutil.move(f"train2017/{f}", f"coco_subset/{f}")
shutil.rmtree("train2017")
print("Kept:", len(os.listdir("coco_subset")))
```

### Option C — Full COCO 2017 (~10 min, 18 GB)

Only if you have Colab Pro disk space:

```bash
!wget -q http://images.cocodataset.org/zips/train2017.zip
!unzip -q train2017.zip -d /content/
```

---

## Step 5 — Train

### Quick demo run (~90 min on T4)

```python
!python scripts/train_model.py \
    --image-dir /content/coco_subset \
    --image-size 128 \
    --message-length 32 \
    --batch-size 12 \
    --epochs 50 \
    --steps-per-epoch 200 \
    --model-dir ./models
```

### Full proposal run (~6 h on T4)

```python
!python scripts/train_model.py \
    --image-dir /content/coco_subset \
    --image-size 128 \
    --message-length 32 \
    --batch-size 12 \
    --epochs 200 \
    --steps-per-epoch 500 \
    --model-dir ./models
```

### What to watch

After every epoch the script prints something like:

```
[epoch  37] time=72.3s  L_M=0.0214 L_I=0.0008 L_G=0.6912 L_D=1.3812
            bit_acc=98.74% PSNR=42.31dB
```

Healthy signs:
- `bit_acc` climbs from ~50% → ~95% by epoch 20–40, then keeps rising.
- `PSNR` climbs from ~25 dB → ~40+ dB.
- `L_M` (message loss) drops toward 0.
- `L_I` (image loss) stays small and stable.
- `L_D` (discriminator) hovers around `1.38` (= 2 × log 2). If it crashes
  to 0, the discriminator is winning too hard — that's fine, the encoder
  will adapt.

Unhealthy signs:
- `bit_acc` stuck at 50% after 20 epochs → restart with a smaller learning
  rate (`--lr-encdec 5e-4`).
- `PSNR` < 25 dB at epoch 50 → check λ_I; try `--lambda-i 1.5`.
- `NaN` anywhere → training diverged; restart.

### Per-epoch sample images

The script writes a 3-panel image to `./models/samples/epoch_NNN.png` every
epoch — **cover | stego | 10× diff**. Glance at these to confirm the
encoder is producing visually-clean stego images, not artifacts.

---

## Step 6 — Download the trained weights

Two minutes after the run finishes:

```python
# Zip the weights folder
!zip -r models.zip models/
# Trigger download
from google.colab import files
files.download("models.zip")
```

You'll get a `models.zip` containing:

```
models/
├── encoder.index
├── encoder.data-00000-of-00001
├── decoder.index
├── decoder.data-00000-of-00001
├── discriminator.index
├── discriminator.data-00000-of-00001
└── samples/
    └── epoch_*.png
```

Unzip this into the **root of your project** (`PixelGuard/models/`).

---

## Step 7 — Activate the trained model in your SaaS

Edit `backend/.env`:

```env
STEGO_METHOD=neural
MODEL_PATH=./models
MESSAGE_LENGTH=32
IMAGE_SIZE=128
```

Restart uvicorn:

```powershell
uvicorn app.main:app --reload --port 8000
```

You should see logs like:

```
[stego/neural] loaded encoder from ./models\encoder
[stego/neural] loaded decoder from ./models\decoder
```

Test from the React UI — encode an image, download it, upload to /decode.
This time the decoder should recover the tracking ID after JPEG / blur /
resize.

---

## Step 8 — Measure robustness for the report

A built-in endpoint runs the standard battery of distortions:

```bash
curl -X POST http://localhost:8000/api/v1/encode/test-robustness \
  -F file=@sample.jpg \
  -F tracking_id=deadbeef
```

Returns per-distortion bit accuracy. Use the numbers in your report's
Results section to back the claims from Proposal § 6.

---

## Troubleshooting

| Symptom                               | Cause / Fix                                            |
|---------------------------------------|--------------------------------------------------------|
| Colab disconnects after ~6 h          | Free-tier limit. Save weights early, resume on new account. |
| OOM during training                   | Lower batch size to 8 or image size to 96.             |
| `bit_acc` stuck at ~50% after 30 ep   | Drop `--lr-encdec` to 5e-4; lower `--lambda-i` to 0.4.  |
| Encoded image has visible noise       | Raise `--lambda-i` to 1.5 or run more epochs.          |
| Decoder fine in train, bad in service | Check `IMAGE_SIZE` in `.env` matches training size.    |
| `weights_loaded: false` in response   | `MODEL_PATH` wrong; files not unzipped to right place. |

---

## Curriculum option (advanced)

The paper gets best results with a **6-phase curriculum** rather than
combined-from-the-start. Currently we use combined; you can split into
phases by passing `--epochs 30` per phase and editing `noise_layer.py`
to fix `NoiseLayer(kind=...)` to a specific distortion. Each phase takes
~30 min on T4; total ~3 h. See the README of any HiDDeN reimplementation
on GitHub for the canonical curriculum order.

---

## Citing this in your report

> "We trained the HiDDeN-style encoder/decoder/discriminator end-to-end
> on a 10,000-image subset of COCO 2017. Training used the combined
> noise-layer recipe with λ_I = 0.7 and λ_G = 0.001 (Zhu et al. 2018),
> for N epochs on a single NVIDIA T4 GPU (~Y h wall-clock). Final bit
> accuracy on held-out images was Z%, with mean PSNR of 41.2 dB."

Fill in N, Y, Z from your actual runs.
