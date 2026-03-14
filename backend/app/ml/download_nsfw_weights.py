# backend/app/ml/download_nsfw_weights.py
import os
import requests
import torch
from pathlib import Path

def download_nsfw_weights():
    """Download pre-trained NSFW weights for EfficientNet"""
    
    # Create models directory
    models_dir = Path("./models/nsfw")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    weights_path = models_dir / "nsfw_efficientnet.pth"
    
    # Option 1: Download from a public source (if available)
    # You need to find actual NSFW weights. Here are some options:
    
    print("="*60)
    print("Downloading NSFW weights for EfficientNet")
    print("="*60)
    
    # Option 1: From NSFW-JS converted to PyTorch
    # Search on HuggingFace: https://huggingface.co/models?search=nsfw
    urls = [
        "https://huggingface.co/Freditheye/NSFW-Pytorch-Model/resolve/main/nsfw_model.pth",
        # Add more URLs if you find them
    ]
    
    for url in urls:
        try:
            print(f"Trying to download from: {url}")
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(weights_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"✅ Downloaded to {weights_path}")
                return str(weights_path)
        except:
            continue
    
    # Option 2: Manual download instructions
    print("\n" + "="*60)
    print("Manual Download Required")
    print("="*60)
    print("\nPlease download NSFW weights from one of these sources:")
    print("1. HuggingFace: https://huggingface.co/models?search=nsfw")
    print("2. Convert from GantMan's model: https://github.com/GantMan/nsfw_model")
    print("3. Use this Colab notebook to convert: https://colab.research.google.com/")
    print("\nAfter downloading, place the file at:")
    print(f"   {weights_path.absolute()}")
    print("\nThen update efficientnet_model.py to use this path.")
    
    return None

if __name__ == "__main__":
    download_nsfw_weights()