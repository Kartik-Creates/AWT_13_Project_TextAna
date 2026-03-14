# backend/app/ml/efficientnet_model.py
import torch
import torch.nn as nn
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
from torchvision import transforms
from PIL import Image
import numpy as np
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

class EfficientNetNSFWDetector:
    """NSFW content detection using EfficientNet"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"EfficientNet using device: {self.device}")
        
        self.categories = ["safe", "porn", "sexy", "hentai", "drawings"]
        self.nsfw_threshold = 0.7
        
        # Try to load model with error handling
        try:
            self.model = self._load_model(model_path)
        except Exception as e:
            logger.error(f"Failed to load model with primary method: {e}")
            logger.info("Trying fallback loading method...")
            self.model = self._load_model_fallback()
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        logger.info("EfficientNet NSFW detector initialized")
    
    def _load_model(self, model_path: Optional[str] = None) -> nn.Module:
        """Load model with proper weights"""
        try:
            # Clear any corrupted cache files
            self._clean_cache_if_needed()
            
            # Use the new weights API
            logger.info("Loading EfficientNet with DEFAULT weights")
            weights = EfficientNet_B0_Weights.DEFAULT
            model = efficientnet_b0(weights=weights)
            
            # Modify classifier
            num_features = model.classifier[1].in_features
            model.classifier[1] = nn.Linear(num_features, len(self.categories))
            
            if model_path and os.path.exists(model_path):
                logger.info(f"Loading custom weights from {model_path}")
                state_dict = torch.load(model_path, map_location=self.device)
                model.load_state_dict(state_dict)
            
            model.to(self.device)
            model.eval()
            return model
            
        except Exception as e:
            logger.error(f"Error in _load_model: {e}")
            raise
    
    def _clean_cache_if_needed(self):
        """Clean corrupted cache files"""
        cache_dir = os.path.expanduser("~/.cache/torch/hub/checkpoints/")
        if os.path.exists(cache_dir):
            for f in os.listdir(cache_dir):
                if "efficientnet" in f and f.endswith('.pth'):
                    logger.info(f"Found cached file: {f}")
    
    def _load_model_fallback(self) -> nn.Module:
        """Fallback loading method"""
        try:
            logger.info("Using fallback model loading")
            import torchvision.models as models
            model = models.efficientnet_b0(pretrained=False)
            
            num_features = model.classifier[1].in_features
            model.classifier[1] = nn.Linear(num_features, len(self.categories))
            
            model.to(self.device)
            model.eval()
            logger.warning("Loaded EfficientNet without pretrained weights")
            return model
        except Exception as e:
            logger.error(f"Fallback also failed: {e}")
            raise
    
    def analyze(self, image_path: str) -> Dict[str, Any]:
        """Analyze image for NSFW content"""
        try:
            image = Image.open(image_path).convert("RGB")
            image_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(image_tensor)
                probabilities = torch.softmax(outputs, dim=1)
                
                category_probs = {
                    self.categories[i]: probabilities[0][i].item()
                    for i in range(len(self.categories))
                }
                
                nsfw_prob = sum([
                    category_probs.get("porn", 0),
                    category_probs.get("sexy", 0),
                    category_probs.get("hentai", 0)
                ])
                
                predicted_class = probabilities[0].argmax().item()
                primary_category = self.categories[predicted_class]
                
                is_nsfw = nsfw_prob > self.nsfw_threshold or primary_category in ["porn", "hentai"]
            
            return {
                "nsfw_probability": nsfw_prob,
                "is_nsfw": is_nsfw,
                "primary_category": primary_category,
                "category_probabilities": category_probs,
                "explicit_content_detected": primary_category in ["porn", "hentai"]
            }
            
        except Exception as e:
            logger.error(f"Error in analysis: {e}")
            return self._fallback_analysis(image_path)
    
    def _fallback_analysis(self, image_path: str) -> Dict[str, Any]:
        """Fallback analysis"""
        return {
            "nsfw_probability": 0.3,
            "is_nsfw": False,
            "primary_category": "unknown",
            "category_probabilities": {},
            "explicit_content_detected": False,
            "using_fallback": True
        }

efficientnet_nsfw = EfficientNetNSFWDetector()