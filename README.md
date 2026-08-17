# PixelGuard

PixelGuard is a Pytorch implementation of the "HiDDeN: Hiding Data With Deep Networks" architecture (https://arxiv.org/abs/1807.09937). It provides tools for hiding data and messages within images using deep neural networks, maintaining the original visual fidelity while ensuring robustness against different image distortions.

## Group Members

- M.A.P. Imalsha - EG/2021/4562
- A.R.M.D.D. Kumara - EG/2021/4622
- W.G.I.S. Madusanka - EG/2021/4662
- R.L.D.T.H. Surasinghe - EG/2021/4820

## Features

- **Encoder/Decoder Model:** Train models to seamlessly hide and extract messages within images.
- **Robustness (Noise Layers):** Supports applying noise to watermarked images during training (Crop, Cropout, Dropout, Resize, Jpeg, etc.) to ensure robust hidden messages.
- **REST API:** Includes a FastAPI-based REST API to easily encode and decode messages interactively.
- **Tensorboard Integration:** Built-in support for visualizing training metrics using Tensorboard.

## Requirements

- Python 3.6+
- [Pytorch](https://pytorch.org/) 1.0 with TorchVision
- FastAPI and Uvicorn (for the API)
- Optional: TensorboardX and Tensorboard to visualize the training.

Install the necessary dependencies using:
```bash
pip install -r requirements.txt
```

## Data

The training requires a dataset of images (e.g., COCO dataset). We recommend using 10,000 images for training and 1,000 images for validation. 

The data directory should have the following structure:
```
<data_root>/
  train/
    train_class/
      train_image1.jpg
      train_image2.jpg
      ...
  val/
    val_class/
      val_image1.jpg
      val_image2.jpg
      ...
```
This structure allows the use of standard `torchvision` data loaders without changes.

## How to Run

### 1. Training via CLI

To start a new training run, use the `main.py` script:
```bash
python main.py new --name <experiment_name> --data-dir <data_root> --batch-size <b> 
```
- By default, tensorboard logging is disabled. To enable it, append the `--tensorboard` switch.
- Each run creates a folder in `./runs/<experiment_name date-and-time>` and stores all information and checkpoints there.

If you want to continue training from an incomplete run, use:
```bash
python main.py continue --folder <incomplete_run_folder>
```

For a detailed description of all available parameters:
```bash
python main.py --help
```

#### Running with Noise Layers

You can specify noise layers configuration to make the model robust against distortions. Use the `--noise` switch followed by the configuration of noise layer(s).

For instance:
```bash
python main.py new --name 'combined-noise' --data-dir /data/ --batch-size 12 --noise 'crop((0.2,0.3),(0.4,0.5))+cropout((0.11,0.22),(0.33,0.44))+dropout(0.2,0.3)+jpeg()'
```
*Note: It is important to use quotes around the noise configuration and avoid redundant spaces. If you want to stack several noise layers, specify them using `+`.*

### 2. Running the REST API

We provide a REST API using FastAPI to encode and decode messages in images easily, without needing to interact directly with the code.

1. Ensure requirements are installed:
```bash
pip install -r requirements.txt
```

2. Start the FastAPI server:
```bash
uvicorn api:app --reload
```

3. Open your web browser and navigate to:
   `http://127.0.0.1:8000/docs`
   
   Here, you can interact with the API endpoints (`/encode` and `/decode`) directly via the built-in Swagger UI.
