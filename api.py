import torch
import numpy as np
import os
import io
import string
import random
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image
import torchvision.transforms.functional as TF
from pymongo import MongoClient
from dotenv import load_dotenv

import utils
from model.hidden import Hidden
from noise_layers.noiser import Noiser

app = FastAPI(title="HiDDeN API")

# Global variables for the model and DB
device = None
hidden_net = None
hidden_config = None
db_collection = None

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
def load_model_and_db():
    global device, hidden_net, hidden_config, db_collection
    
    # Load environment variables
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI")
    if mongo_uri and mongo_uri != "your_mongodb_atlas_connection_string_here":
        try:
            client = MongoClient(mongo_uri)
            db = client.pixelguard
            db_collection = db.payloads
            print("Connected to MongoDB Atlas")
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
    else:
        print("MongoDB URI not set or is placeholder. DB features won't work.")
    
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

def attempt_encode_decode(image_tensor, unique_id):
    """Attempts to encode the unique_id into the image and then decode it. Returns encoded image if match, else None."""
    bits = string_to_bits(unique_id, hidden_config.message_length)
    message_tensor = torch.Tensor([bits]).to(device)
    
    with torch.no_grad():
        encoded_images = hidden_net.encoder_decoder.encoder(image_tensor, message_tensor)
        
        # Test decoding
        decoded_messages = hidden_net.encoder_decoder.decoder(encoded_images)
        
    decoded_rounded = decoded_messages.detach().cpu().numpy().round().clip(0, 1)
    decoded_bits = decoded_rounded[0].tolist()
    decoded_string = bits_to_string(decoded_bits)
    
    if decoded_string.startswith(unique_id):
        # Success
        encoded_images = encoded_images.cpu()
        encoded_images = (encoded_images + 1) / 2 # Scale back to [0, 1]
        encoded_images = encoded_images.clamp(0, 1)
        encoded_pil = TF.to_pil_image(encoded_images[0])
        return encoded_pil
    return None

@app.post("/encode")
async def encode_image(
    image: UploadFile = File(...),
    name: str = Form(...),
    image_name: str = Form(...),
    owner_info: str = Form(...)
):
    if db_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured.")

    image_bytes = await image.read()
    image_pil = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    image_np = np.array(image_pil)
    
    # Crop to expected size
    image_cropped = center_crop(image_np, hidden_config.H, hidden_config.W)
    image_tensor = TF.to_tensor(image_cropped).to(device)
    image_tensor = image_tensor * 2 - 1  # transform from [0, 1] to [-1, 1]
    image_tensor.unsqueeze_(0)
    
    max_attempts = 20
    encoded_pil = None
    successful_id = None
    
    for attempt in range(max_attempts):
        unique_id = ''.join(random.choices(string.ascii_letters, k=2))
        
        encoded_pil = attempt_encode_decode(image_tensor, unique_id)
        if encoded_pil is not None:
            successful_id = unique_id
            break

    if not successful_id:
        raise HTTPException(status_code=500, detail="Failed to encode reliably after 20 attempts. Please try a different image.")
        
    # Save to MongoDB
    payload = {
        "unique_id": successful_id,
        "name": name,
        "image_name": image_name,
        "owner_info": owner_info
    }
    db_collection.insert_one(payload)
    
    buf = io.BytesIO()
    encoded_pil.save(buf, format="PNG")
    buf.seek(0)
    
    return StreamingResponse(buf, media_type="image/png", headers={"Content-Disposition": f"attachment; filename=encoded_{image.filename}"})

@app.post("/decode")
async def decode_image(image: UploadFile = File(...)):
    if db_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured.")

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
    
    if not decoded_message or len(decoded_message) < 2:
        return {"error": "Could not decode any ID from the image."}
        
    extracted_id = decoded_message[:2]
    
    # Lookup in MongoDB
    record = db_collection.find_one({"unique_id": extracted_id}, {"_id": 0})
    if record:
        return {"success": True, "payload": record}
    else:
        return {"success": False, "error": f"ID '{extracted_id}' decoded, but no matching payload found in database."}
