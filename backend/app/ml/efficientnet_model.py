# backend/app/ml/efficientnet_model.py
"""
NSFW image detection using Falconsai/nsfw_image_detection (ViT-based).

This replaces the old randomly-initialized EfficientNet classifier that
never had trained NSFW weights. The Falconsai model is a Vision Transformer
fine-tuned specifically for NSFW classification with two classes: 'nsfw' and 'normal'.
"""

import torch
from PIL import Image
from typing import Dict, Any, Optional
import logging
import os

from .model_loader import model_loader

logger = logging.getLogger(__name__)


class EfficientNetNSFWDetector:
    """NSFW content detection using Falconsai/nsfw_image_detection (ViT).
    
    Despite the class name (kept for backward compat), this now uses a
    properly trained ViT model from HuggingFace instead of the old
    randomly-initialized EfficientNet head.
    """
    
    def __init__(self):
        self.device = model_loader.device
        logger.info(f"NSFW Detector using device: {self.device}")
        
        self.nsfw_threshold = 0.5
        self.categories = ["normal", "nsfw"]
        
        try:
            self.model, self.processor = model_loader.load_nsfw_model()
            self._model_loaded = True
            logger.info("NSFW detector initialized with Falconsai model")
        except Exception as e:
            logger.error(f"Failed to load NSFW model: {e}")
            self._model_loaded = False
    
    def analyze(self, image_path: str) -> Dict[str, Any]:
        """Analyze image for NSFW content.
        
        Returns dict with:
          nsfw_probability          – float 0-1
          is_nsfw                   – bool
          primary_category          – 'nsfw' or 'normal'
          category_probabilities    – dict {'nsfw': float, 'normal': float}
          explicit_content_detected – bool (high-confidence NSFW)
        """
        if not self._model_loaded:
            logger.warning("NSFW model not loaded, using conservative fallback")
            return self._fallback_analysis(image_path)
        
        try:
            image = Image.open(image_path).convert("RGB")
            
            # Preprocess with the ViT processor
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=1).squeeze(0)
            
            # Get the model's id2label mapping
            id2label = self.model.config.id2label
            
            # Build category probabilities
            category_probs = {}
            for i in range(len(probabilities)):
                label = id2label.get(i, f"class_{i}").lower()
                category_probs[label] = round(probabilities[i].item(), 4)
            
            # Get NSFW probability — look for 'nsfw' label
            nsfw_prob = category_probs.get("nsfw", 0.0)
            normal_prob = category_probs.get("normal", 1.0)
            
            # Determine primary category  
            predicted_idx = probabilities.argmax().item()
            primary_category = id2label.get(predicted_idx, "unknown").lower()
            
            is_nsfw = nsfw_prob >= self.nsfw_threshold
            
            return {
                "nsfw_probability": round(nsfw_prob, 4),
                "is_nsfw": is_nsfw,
                "primary_category": primary_category,
                "category_probabilities": category_probs,
                "explicit_content_detected": nsfw_prob >= 0.8,
                "model_used": "Falconsai/nsfw_image_detection",
            }
            
        except Exception as e:
            logger.error(f"Error in NSFW analysis: {e}", exc_info=True)
            return self._fallback_analysis(image_path)
    
    def _fallback_analysis(self, image_path: str) -> Dict[str, Any]:
        """Fallback: conservative — flag as needing review."""
        try:
            Image.open(image_path).verify()
            return {
                "nsfw_probability": 0.5,
                "is_nsfw": False,
                "primary_category": "review_needed",
                "category_probabilities": {},
                "explicit_content_detected": False,
                "using_fallback": True,
            }
        except Exception:
            # Can't even open the image — treat as suspicious
            return {
                "nsfw_probability": 0.8,
                "is_nsfw": True,
                "primary_category": "invalid_image",
                "category_probabilities": {},
                "explicit_content_detected": True,
                "using_fallback": True,
            }


# Global instance
efficientnet_nsfw = EfficientNetNSFWDetector()