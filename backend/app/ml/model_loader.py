import torch
import torch.nn as nn
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
        """Load toxicity model and tokenizer.

        Primary:  unitary/multilingual-toxic-xlm-roberta  (supports Hindi + 100 languages)
        Fallback: unitary/toxic-bert                      (English-only)
        Both use the same 6 Jigsaw toxicity labels:
            toxic, severe_toxic, obscene, threat, insult, identity_hate
        """
        model_key = "distilbert"

        if model_key in self._models:
            return self._models[model_key]

        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        # Try multilingual model first (handles Hindi, Hinglish, etc.)
        primary = os.getenv("TOXICITY_MODEL", "unitary/multilingual-toxic-xlm-roberta")
        fallback = "unitary/toxic-bert"

        for model_name in [primary, fallback]:
            try:
                logger.info(f"Loading toxicity model: {model_name}")
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForSequenceClassification.from_pretrained(model_name)
                model.to(self.device)
                model.eval()

                self._models[model_key] = (model, tokenizer)
                logger.info(f"Toxicity model loaded successfully ({model_name})")
                return model, tokenizer

            except Exception as e:
                logger.warning(f"Could not load {model_name}: {e}")
                if model_name == fallback:
                    raise  # both failed
                logger.info(f"Falling back to {fallback}")
    
    def load_clip(self) -> Tuple[Any, Any]:
        """Load CLIP model"""
        model_key = "clip"
        
        if model_key in self._models:
            return self._models[model_key]
        
        try:
            import clip
            
            logger.info("Loading CLIP model...")
            
            model, preprocess = clip.load("ViT-B/32", device=self.device)
            model.eval()
            
            self._models[model_key] = (model, preprocess)
            logger.info("CLIP loaded successfully")
            
            return model, preprocess
            
        except Exception as e:
            logger.error(f"Error loading CLIP: {e}")
            raise
    
    def load_nsfw_model(self) -> Tuple[Any, Any]:
        """Load NSFW image classification model (Falconsai/nsfw_image_detection)"""
        model_key = "nsfw"
        
        if model_key in self._models:
            return self._models[model_key]
        
        try:
            from transformers import AutoModelForImageClassification, ViTImageProcessor
            
            model_name = os.getenv("NSFW_MODEL", "Falconsai/nsfw_image_detection")
            logger.info(f"Loading NSFW model: {model_name}")
            
            processor = ViTImageProcessor.from_pretrained(model_name)
            model = AutoModelForImageClassification.from_pretrained(model_name)
            
            model.to(self.device)
            model.eval()
            
            self._models[model_key] = (model, processor)
            logger.info(f"NSFW model loaded successfully ({model_name})")
            
            return model, processor
            
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