import torch
import torch.nn as nn
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
import clip
import logging
import os
from typing import Optional, Tuple, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelLoader:
    """Singleton class to manage ML model loading and caching"""
    
    _instance = None
    _models = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
        # Model paths
        self.models_dir = Path(os.getenv("MODELS_DIR", "./models"))
        self.models_dir.mkdir(exist_ok=True)
    
    def load_distilbert(self) -> Tuple[Any, Any]:
        """Load DistilBERT model and tokenizer"""
        model_key = "distilbert"
        
        if model_key in self._models:
            return self._models[model_key]
        
        try:
            logger.info("Loading DistilBERT model...")
            
            model_name = os.getenv("DISTILBERT_MODEL", "distilbert-base-uncased")
            tokenizer = DistilBertTokenizer.from_pretrained(model_name)
            model = DistilBertForSequenceClassification.from_pretrained(
                model_name, 
                num_labels=2  # Binary classification for toxicity
            )
            
            model.to(self.device)
            model.eval()
            
            self._models[model_key] = (model, tokenizer)
            logger.info("DistilBERT loaded successfully")
            
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"Error loading DistilBERT: {e}")
            raise
    
    def load_efficientnet(self, model_path=None):
        """Load EfficientNet NSFW model"""
        model_key = "efficientnet"
        
        if model_key in self._models:
            return self._models[model_key]
        
        from app.ml.efficientnet_model import EfficientNetNSFWDetector
        model = EfficientNetNSFWDetector(model_path)
        
        self._models[model_key] = model
        return model
    
    def load_clip(self) -> Tuple[Any, Any]:
        """Load CLIP model"""
        model_key = "clip"
        
        if model_key in self._models:
            return self._models[model_key]
        
        try:
            logger.info("Loading CLIP model...")
            
            model, preprocess = clip.load("ViT-B/32", device=self.device)
            model.eval()
            
            self._models[model_key] = (model, preprocess)
            logger.info("CLIP loaded successfully")
            
            return model, preprocess
            
        except Exception as e:
            logger.error(f"Error loading CLIP: {e}")
            raise
    
    def load_nsfw_model(self) -> Any:
        """Load NSFW detection model"""
        model_key = "nsfw"
        
        if model_key in self._models:
            return self._models[model_key]
        
        try:
            logger.info("Loading NSFW detection model...")
            
            # Using EfficientNet for NSFW detection
            import torchvision.models as models
            model = models.efficientnet_b0(pretrained=True)
            
            # Modify last layer for binary NSFW classification
            num_features = model.classifier[1].in_features
            model.classifier[1] = nn.Linear(num_features, 2)
            
            # Load pretrained weights (in production, load actual NSFW weights)
            # model.load_state_dict(torch.load("path/to/nsfw_weights.pth"))
            
            model.to(self.device)
            model.eval()
            
            self._models[model_key] = model
            logger.info("NSFW model loaded successfully")
            
            return model
            
        except Exception as e:
            logger.error(f"Error loading NSFW model: {e}")
            raise
    
    def unload_models(self):
        """Unload models to free memory"""
        self._models.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Models unloaded")

# Global instance
model_loader = ModelLoader()