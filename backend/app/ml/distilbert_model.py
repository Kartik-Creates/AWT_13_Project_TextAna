import torch
import numpy as np
from typing import Tuple, List, Dict, Any
import logging
from .model_loader import model_loader
import re

logger = logging.getLogger(__name__)

class DistilBERTAnalyzer:
    """Text analysis using DistilBERT"""
    
    def __init__(self):
        self.model, self.tokenizer = model_loader.load_distilbert()
        self.device = model_loader.device
        
        # Toxicity thresholds
        self.toxicity_threshold = 0.7
        self.hate_threshold = 0.6
        
        # Keyword patterns for flagged phrases
        self.flagged_patterns = {
            r'\b(hate|hates|hatred)\b': 'hate_speech',
            r'\b(kill|murder|death|die)\b': 'violence',
            r'\b(racist|racism)\b': 'discrimination',
            r'\b(sexist|sexism)\b': 'discrimination',
            r'\b(suicide|self.?harm)\b': 'self_harm',
            r'\b(porn|nsfw|explicit)\b': 'sexual_content',
            r'\b(scam|fraud|phishing)\b': 'scam',
            r'\b(terrorist|terrorism)\b': 'terrorism'
        }
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text for toxic content
        Returns: Dict with scores and flagged content
        """
        try:
            # Tokenize input
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)
            
            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                
                # Get toxicity score (assuming class 1 is toxic)
                toxicity_score = probabilities[0][1].item()
                
                # Get confidence
                confidence = torch.max(probabilities).item()
            
            # Extract flagged phrases
            flagged_phrases = self._extract_flagged_phrases(text)
            
            # Determine primary category
            category = self._determine_category(toxicity_score, flagged_phrases)
            
            return {
                "toxicity_score": toxicity_score,
                "confidence": confidence,
                "category": category,
                "flagged_phrases": flagged_phrases,
                "is_toxic": toxicity_score > self.toxicity_threshold
            }
            
        except Exception as e:
            logger.error(f"Error in DistilBERT analysis: {e}")
            return self._fallback_analysis(text)
    
    def _extract_flagged_phrases(self, text: str) -> List[str]:
        """Extract potentially problematic phrases"""
        flagged = []
        text_lower = text.lower()
        
        for pattern, category in self.flagged_patterns.items():
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                phrase = match.group()
                if phrase and len(phrase) > 2:  # Ignore very short matches
                    flagged.append({
                        "phrase": phrase,
                        "category": category
                    })
        
        return flagged
    
    def _determine_category(self, score: float, flagged: List[str]) -> str:
        """Determine the content category"""
        if flagged:
            # Get most severe category from flagged phrases
            categories = [f["category"] for f in flagged]
            severity_order = [
                "terrorism", "violence", "self_harm", "hate_speech",
                "discrimination", "sexual_content", "scam"
            ]
            
            for severe in severity_order:
                if severe in categories:
                    return severe
            
            return categories[0] if categories else "toxic"
        
        if score > 0.9:
            return "highly_toxic"
        elif score > 0.7:
            return "toxic"
        elif score > 0.5:
            return "questionable"
        else:
            return "safe"
    
    def _fallback_analysis(self, text: str) -> Dict[str, Any]:
        """Fallback analysis when model fails"""
        logger.warning("Using fallback text analysis")
        
        # Simple keyword-based detection
        flagged = self._extract_flagged_phrases(text)
        
        return {
            "toxicity_score": 0.5 if flagged else 0.1,
            "confidence": 0.5,
            "category": "flagged" if flagged else "unknown",
            "flagged_phrases": flagged,
            "is_toxic": bool(flagged)
        }

# Global instance
distilbert_analyzer = DistilBERTAnalyzer()