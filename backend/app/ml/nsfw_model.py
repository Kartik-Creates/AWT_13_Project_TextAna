# backend/app/ml/nsfw_model.py
"""NSFW detection wrapper that delegates to the EfficientNet-based detector."""

from PIL import Image
from typing import Dict, Any
import logging

from app.ml.efficientnet_model import efficientnet_nsfw

logger = logging.getLogger(__name__)


class NSFWDetector:
    """NSFW content detection wrapper.
    
    Primary (and only) model: Falconsai/nsfw_image_detection (via efficientnet_nsfw)
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
            logger.error(f"NSFW analysis failed, using conservative fallback: {e}")
            return self._fallback_analysis(image_path)
    
    def _fallback_analysis(self, image_path: str) -> Dict[str, Any]:
        """Fallback — conservative (flag for review, don't auto-approve)."""
        logger.warning("Using conservative NSFW fallback (no secondary model)")

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


# Global instance
nsfw_detector = NSFWDetector()