# backend/app/ml/download_models.py
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
import os
from pathlib import Path

def download_models():
    """Download all required models"""
    models_dir = Path("./models")
    models_dir.mkdir(exist_ok=True)
    
    print("1. Downloading XLM-RoBERTa toxicity model...")
    model_name = "unitary/multilingual-toxic-xlm-roberta"
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model.save_pretrained(models_dir / "xlm-roberta-toxicity")
    tokenizer.save_pretrained(models_dir / "xlm-roberta-toxicity")
    
    print("2. CLIP will be downloaded on first use")
    print("3. For NSFW model, you need to manually download from:")
    print("   https://github.com/GantMan/nsfw_model")
    print("\nAll done!")

if __name__ == "__main__":
    download_models()