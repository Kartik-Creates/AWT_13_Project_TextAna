# backend/app/ml/nsfw_model.py
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms
from typing import Dict, Any
import logging

from app.ml.efficientnet_model import efficientnet_nsfw

logger = logging.getLogger(__name__)

class NSFWDetector:
    """NSFW content detection in images using EfficientNet"""
    
    def __init__(self):
        """
        Initialize NSFW detector using EfficientNet
        """
        logger.info("Initializing NSFWDetector with EfficientNet")
        
        # Use the EfficientNet detector
        self.detector = efficientnet_nsfw
        
        # For backward compatibility
        self.nsfw_threshold = self.detector.nsfw_threshold
        self.categories = self.detector.categories
        
        logger.info(f"NSFWDetector initialized with categories: {self.categories}")
        logger.info(f"Using device: {self.detector.device}")
    
    def analyze(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze image for NSFW content using EfficientNet
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with NSFW analysis results
        """
        try:
            # Delegate to EfficientNet detector
            result = self.detector.analyze(image_path)
            
            # Add additional metadata
            result["model_used"] = "EfficientNet-B0"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in NSFW analysis: {e}")
            return self._fallback_analysis(image_path)
    
    def _fallback_analysis(self, image_path: str) -> Dict[str, Any]:
        """
        Fallback analysis when EfficientNet fails
        """
        logger.warning("Using fallback NSFW detection")
        
        try:
            # Try CLIP as secondary fallback
            clip_result = self._clip_fallback(image_path)
            if clip_result:
                return clip_result
        except:
            pass
        
        # Ultimate fallback - conservative approach
        try:
            image = Image.open(image_path)
            return {
                "nsfw_probability": 0.3,
                "is_nsfw": False,
                "primary_category": "unknown",
                "confidence": 0.5,
                "category_probabilities": {},
                "explicit_content_detected": False,
                "using_fallback": True
            }
        except:
            return {
                "nsfw_probability": 0.8,
                "is_nsfw": True,
                "primary_category": "invalid",
                "confidence": 0.0,
                "category_probabilities": {},
                "explicit_content_detected": True,
                "using_fallback": True
            }
    
    def _clip_fallback(self, image_path: str) -> Dict[str, Any]:
        """
        Use CLIP for NSFW detection as secondary fallback
        """
        try:
            import clip
            from PIL import Image
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model, preprocess = clip.load("ViT-B/32", device=device)
            
            image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)
            
            # NSFW prompts
            prompts = [
                "a normal safe photo",
                "pornography",
                "nudity",
                "explicit sexual content",
                "violence and gore"
            ]
            
            text = clip.tokenize(prompts).to(device)
            
            with torch.no_grad():
                image_features = model.encode_image(image)
                text_features = model.encode_text(text)
                
                image_features /= image_features.norm(dim=-1, keepdim=True)
                text_features /= text_features.norm(dim=-1, keepdim=True)
                
                similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            
            nsfw_score = similarity[0, 1:].sum().item()
            
            return {
                "nsfw_probability": nsfw_score,
                "is_nsfw": nsfw_score > 0.5,
                "primary_category": "nsfw" if nsfw_score > 0.5 else "safe",
                "using_clip_fallback": True,
                "confidence": float(similarity[0].max().item()),
                "explicit_content_detected": nsfw_score > 0.6
            }
        except Exception as e:
            logger.error(f"CLIP fallback failed: {e}")
            return None

# Global instance
nsfw_detector = NSFWDetector()