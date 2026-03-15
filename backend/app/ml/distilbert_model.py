import torch
import numpy as np
from typing import Dict, Any, List
import logging
from .model_loader import model_loader

logger = logging.getLogger(__name__)

class DistilBERTAnalyzer:
    """Text toxicity analysis using unitary/toxic-bert.
    
    The model outputs 6 toxicity labels:
      toxic, severe_toxic, obscene, threat, insult, identity_hate
    Each label gets a sigmoid probability (0-1). We aggregate them
    into a single toxicity score and determine the primary category.
    """
    
    # The 6 labels from the Jigsaw toxic-comment dataset
    LABELS = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
    
    # Map model labels → human-readable categories for the decision engine
    CATEGORY_MAP = {
        "toxic": "toxic",
        "severe_toxic": "highly_toxic",
        "obscene": "sexual_content",
        "threat": "violence",
        "insult": "hate_speech",
        "identity_hate": "discrimination",
    }
    
    def __init__(self):
        self.model, self.tokenizer = model_loader.load_distilbert()
        self.device = model_loader.device
        
        # Per-label thresholds (sigmoid probabilities)
        # Lower = more sensitive.  0.5 is the neutral decision boundary.
        self.label_threshold = 0.5
        # Aggregate toxicity threshold for the combined score
        self.toxicity_threshold = 0.45
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text for toxic content using the fine-tuned model.
        
        Returns a dict with:
          toxicity_score  – float 0-1 (max across labels)
          label_scores    – dict of per-label sigmoid scores
          is_toxic        – bool
          category        – primary category string
          flagged_labels  – list of labels that exceeded their threshold
          confidence      – float 0-1
        """
        try:
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)
            
            # Forward pass
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits  # shape: (1, 6)
                
                # Sigmoid for multi-label (NOT softmax — each label is independent)
                probabilities = torch.sigmoid(logits).squeeze(0)  # shape: (6,)
            
            # Build per-label score dict
            label_scores = {}
            flagged_labels = []
            for i, label in enumerate(self.LABELS):
                score = probabilities[i].item()
                label_scores[label] = round(score, 4)
                if score >= self.label_threshold:
                    flagged_labels.append(label)
            
            # Aggregate toxicity score = max across all labels
            toxicity_score = max(label_scores.values())
            
            # Determine primary category from highest-scoring label
            primary_label = max(label_scores, key=label_scores.get)
            category = self._determine_category(toxicity_score, primary_label, flagged_labels)
            
            is_toxic = toxicity_score >= self.toxicity_threshold or len(flagged_labels) > 0
            
            return {
                "toxicity_score": round(toxicity_score, 4),
                "label_scores": label_scores,
                "is_toxic": is_toxic,
                "category": category,
                "flagged_labels": flagged_labels,
                "confidence": round(toxicity_score if is_toxic else (1.0 - toxicity_score), 4),
                "flagged_phrases": [],  # kept for interface compat; rule engine handles keywords
            }
            
        except Exception as e:
            logger.error(f"Error in toxicity analysis: {e}", exc_info=True)
            return self._fallback_analysis(text)
    
    def _determine_category(self, score: float, primary_label: str, flagged: List[str]) -> str:
        """Map model output to a human-readable category."""
        if not flagged and score < self.toxicity_threshold:
            return "safe"
        
        # Use the most severe flagged label
        severity_order = [
            "severe_toxic", "threat", "identity_hate", "toxic", "obscene", "insult"
        ]
        for label in severity_order:
            if label in flagged:
                return self.CATEGORY_MAP.get(label, label)
        
        # Fallback to primary label
        return self.CATEGORY_MAP.get(primary_label, "toxic" if score > self.toxicity_threshold else "safe")
    
    def _fallback_analysis(self, text: str) -> Dict[str, Any]:
        """Fallback when model fails — conservative (flag as suspicious)."""
        logger.warning("Using fallback text analysis — marking as suspicious")
        return {
            "toxicity_score": 0.6,
            "label_scores": {label: 0.0 for label in self.LABELS},
            "is_toxic": True,
            "category": "review_needed",
            "flagged_labels": [],
            "confidence": 0.3,
            "flagged_phrases": [],
        }

# Global instance
distilbert_analyzer = DistilBERTAnalyzer()