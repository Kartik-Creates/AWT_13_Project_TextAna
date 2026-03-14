# backend/app/ml/download_models.py
from transformers import DistilBertForSequenceClassification, DistilBertTokenizer
import torch
import os
from pathlib import Path

def download_models():
    """Download all required models"""
    models_dir = Path("./models")
    models_dir.mkdir(exist_ok=True)
    
    print("1. Downloading DistilBERT...")
    model = DistilBertForSequenceClassification.from_pretrained("distilbert-base-uncased")
    tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
    model.save_pretrained(models_dir / "distilbert")
    tokenizer.save_pretrained(models_dir / "distilbert")
    
    print("2. CLIP will be downloaded on first use")
    print("3. For NSFW model, you need to manually download from:")
    print("   https://github.com/GantMan/nsfw_model")
    print("\nAll done!")

if __name__ == "__main__":
    download_models()