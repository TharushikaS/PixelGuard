import torch
import numpy as np
import os
import io
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from PIL import Image
import torchvision.transforms.functional as TF

import utils
from model.hidden import Hidden
from noise_layers.noiser import Noiser

app = FastAPI(title="HiDDeN API")

# Global variables for the model
device = None
hidden_net = None
hidden_config = None

def string_to_bits(text, max_length):
    bits = []
    for char in text:
        bin_val = bin(ord(char))[2:].zfill(8)
        bits.extend([int(b) for b in bin_val])
    if len(bits) > max_length:
        bits = bits[:max_length]
    else:
        bits.extend([0] * (max_length - len(bits)))
    return bits

def bits_to_string(bits):
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8:
            break
        char_val = int("".join([str(int(b)) for b in byte]), 2)
        if char_val == 0:
            break
        chars.append(chr(char_val))
    return "".join(chars)

@app.on_event("startup")
def load_model():
    global device, hidden_net, hidden_config
    
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    
    options_file = 'experiments/jpeg-compression/options-and-config.pickle'
    checkpoint_file = 'experiments/jpeg-compression/checkpoints/epoch-300.pyt'
    
    train_options, hidden_config, noise_config = utils.load_options(options_file)
    noiser = Noiser(noise_config, device)

    checkpoint = torch.load(checkpoint_file, map_location=device)
    hidden_net = Hidden(hidden_config, device, noiser, None)
    utils.model_from_checkpoint(hidden_net, checkpoint)
    
    # Set to evaluation mode
    hidden_net.encoder_decoder.eval()
    print("Model loaded successfully")

def center_crop(img, height, width):
    if img.shape[0] < height or img.shape[1] < width:
        # Pad if smaller
        pad_h = max(0, height - img.shape[0])
        pad_w = max(0, width - img.shape[1])
        img = np.pad(img, ((0, pad_h), (0, pad_w), (0, 0)), mode='constant')
        
    y = img.shape[0] // 2 - height // 2
    x = img.shape[1] // 2 - width // 2
    return img[y:y+height, x:x+width]

@app.post("/encode")
async def encode_image(image: UploadFile = File(...), message: str = Form(...)):
    image_bytes = await image.read()
    image_pil = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    image_np = np.array(image_pil)
    
    # Crop to expected size
    image_cropped = center_crop(image_np, hidden_config.H, hidden_config.W)
    image_tensor = TF.to_tensor(image_cropped).to(device)
    image_tensor = image_tensor * 2 - 1  # transform from [0, 1] to [-1, 1]
    image_tensor.unsqueeze_(0)
    
    bits = string_to_bits(message, hidden_config.message_length)
    message_tensor = torch.Tensor([bits]).to(device)
    
    with torch.no_grad():
        encoded_images = hidden_net.encoder_decoder.encoder(image_tensor, message_tensor)
        
    encoded_images = encoded_images.cpu()
    encoded_images = (encoded_images + 1) / 2 # Scale back to [0, 1]
    encoded_images = encoded_images.clamp(0, 1)
    
    encoded_pil = TF.to_pil_image(encoded_images[0])
    
    buf = io.BytesIO()
    encoded_pil.save(buf, format="PNG")
    buf.seek(0)
    
    return StreamingResponse(buf, media_type="image/png", headers={"Content-Disposition": f"attachment; filename=encoded_{image.filename}"})

@app.post("/decode")
async def decode_image(image: UploadFile = File(...)):
    image_bytes = await image.read()
    image_pil = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    image_np = np.array(image_pil)
    
    image_cropped = center_crop(image_np, hidden_config.H, hidden_config.W)
    image_tensor = TF.to_tensor(image_cropped).to(device)
    image_tensor = image_tensor * 2 - 1  # transform from [0, 1] to [-1, 1]
    image_tensor.unsqueeze_(0)
    
    with torch.no_grad():
        decoded_messages = hidden_net.encoder_decoder.decoder(image_tensor)
        
    decoded_rounded = decoded_messages.detach().cpu().numpy().round().clip(0, 1)
    bits = decoded_rounded[0].tolist()
    
    decoded_message = bits_to_string(bits)
    
    return {"decoded_message": decoded_message}
