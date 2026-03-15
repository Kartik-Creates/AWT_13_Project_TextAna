# backend/app/ml/nsfw_model.py
"""
NSFW detection wrapper that delegates to the EfficientNet (now ViT) detector.
Provides backward-compatible interface and CLIP-based fallback.
"""

import torch
from PIL import Image
from typing import Dict, Any
import logging

from app.ml.efficientnet_model import efficientnet_nsfw

logger = logging.getLogger(__name__)


class NSFWDetector:
    """NSFW content detection wrapper.
    
    Primary: Falconsai/nsfw_image_detection (via efficientnet_nsfw)
    Fallback: CLIP-based zero-shot NSFW detection
    """
    
    def __init__(self):
        logger.info("Initializing NSFWDetector")
        self.detector = efficientnet_nsfw
        self.nsfw_threshold = self.detector.nsfw_threshold
        self.categories = self.detector.categories
        logger.info(f"NSFWDetector initialized, model loaded: {self.detector._model_loaded}")
    
    def analyze(self, image_path: str) -> Dict[str, Any]:
        """Analyze image for NSFW content."""
        try:
            result = self.detector.analyze(image_path)
            result["model_used"] = result.get("model_used", "Falconsai/nsfw_image_detection")
            return result
            
        except Exception as e:
            logger.error(f"Primary NSFW analysis failed: {e}")
            return self._fallback_analysis(image_path)
    
    def _fallback_analysis(self, image_path: str) -> Dict[str, Any]:
        """Fallback: try CLIP, then conservative default."""
        logger.warning("Using fallback NSFW detection")
        
        # Try CLIP-based detection
        try:
            clip_result = self._clip_fallback(image_path)
            if clip_result:
                return clip_result
        except Exception as e:
            logger.error(f"CLIP fallback also failed: {e}")
        
        # Ultimate fallback — conservative (flag for review, don't auto-approve)
        try:
            Image.open(image_path).verify()
            return {
                "nsfw_probability": 0.5,
                "is_nsfw": False,
                "primary_category": "review_needed",
                "confidence": 0.3,
                "category_probabilities": {},
                "explicit_content_detected": False,
                "using_fallback": True,
            }
        except Exception:
            return {
                "nsfw_probability": 0.9,
                "is_nsfw": True,
                "primary_category": "invalid_image",
                "confidence": 0.0,
                "category_probabilities": {},
                "explicit_content_detected": True,
                "using_fallback": True,
            }
    
    def _clip_fallback(self, image_path: str) -> Dict[str, Any]:
        """Use CLIP for zero-shot NSFW detection as secondary fallback."""
        try:
            import clip
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model, preprocess = clip.load("ViT-B/32", device=device)
            
            image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)
            
            prompts = [
                "a normal safe photo",
                "pornography",
                "nudity",
                "explicit sexual content",
                "violence and gore",
            ]
            
            text = clip.tokenize(prompts).to(device)
            
            with torch.no_grad():
                image_features = model.encode_image(image)
                text_features = model.encode_text(text)
                
                image_features /= image_features.norm(dim=-1, keepdim=True)
                text_features /= text_features.norm(dim=-1, keepdim=True)
                
                similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            
            # Sum of all NSFW prompt scores (indices 1-4)
            nsfw_score = similarity[0, 1:].sum().item()
            
            return {
                "nsfw_probability": round(nsfw_score, 4),
                "is_nsfw": nsfw_score > 0.5,
                "primary_category": "nsfw" if nsfw_score > 0.5 else "safe",
                "using_clip_fallback": True,
                "confidence": float(similarity[0].max().item()),
                "explicit_content_detected": nsfw_score > 0.6,
            }
        except Exception as e:
            logger.error(f"CLIP fallback failed: {e}")
            return None


# Global instance
nsfw_detector = NSFWDetector()