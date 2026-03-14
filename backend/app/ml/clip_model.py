import clip
import torch
import numpy as np
from PIL import Image
from typing import Tuple, Dict, Any, Optional
import logging
from .model_loader import model_loader

logger = logging.getLogger(__name__)

class CLIPAnalyzer:
    """Image-text relevance analysis using CLIP"""
    
    def __init__(self):
        self.model, self.preprocess = model_loader.load_clip()
        self.device = model_loader.device
        
        # Relevance threshold
        self.relevance_threshold = 0.25
    
    def analyze(self, text: str, image_path: str) -> Dict[str, Any]:
        """
        Analyze relevance between text and image
        Returns: Dict with similarity scores and analysis
        """
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # Tokenize text
            text_tokens = clip.tokenize([text]).to(self.device)
            
            # Calculate embeddings
            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                text_features = self.model.encode_text(text_tokens)
                
                # Normalize features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                # Calculate similarity
                similarity = (image_features @ text_features.T).item()
                
                # Get top similar concepts (for additional context)
                concepts = self._get_concept_similarity(image_features)
            
            is_relevant = similarity > self.relevance_threshold
            
            return {
                "similarity_score": similarity,
                "is_relevant": is_relevant,
                "relevant_concepts": concepts,
                "mismatch_detected": not is_relevant and similarity < 0.15
            }
            
        except Exception as e:
            logger.error(f"Error in CLIP analysis: {e}")
            return self._fallback_analysis(text, image_path)
    
    def _get_concept_similarity(self, image_features: torch.Tensor) -> list:
        """Get similarity with common concepts"""
        concepts = [
            "text", "screenshot", "meme", "photo", "drawing",
            "person", "animal", "landscape", "food", "product"
        ]
        
        try:
            concept_tokens = clip.tokenize(concepts).to(self.device)
            
            with torch.no_grad():
                concept_features = self.model.encode_text(concept_tokens)
                concept_features = concept_features / concept_features.norm(dim=-1, keepdim=True)
                
                similarities = (image_features @ concept_features.T).squeeze(0)
                
                # Get top 3 concepts
                top_indices = similarities.argsort(descending=True)[:3]
                
                return [
                    {"concept": concepts[idx], "score": similarities[idx].item()}
                    for idx in top_indices
                ]
        except:
            return []
    
    def _fallback_analysis(self, text: str, image_path: str) -> Dict[str, Any]:
        """Fallback analysis"""
        logger.info("Using fallback image-text analysis")
        
        # Simple image validation
        try:
            image = Image.open(image_path)
            image.verify()  # Verify it's a valid image
            
            return {
                "similarity_score": 0.5,
                "is_relevant": True,
                "relevant_concepts": [],
                "mismatch_detected": False
            }
        except:
            return {
                "similarity_score": 0.0,
                "is_relevant": False,
                "relevant_concepts": [],
                "mismatch_detected": True
            }

# Global instance
clip_analyzer = CLIPAnalyzer()