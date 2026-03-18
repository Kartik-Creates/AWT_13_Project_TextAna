"""
Decision Engine for Moderation System
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DecisionEngine:
    """Makes final moderation decisions based on all signals"""
    
    def __init__(self):
        # Thresholds for blocking
        self.block_thresholds = {
            'toxicity': 0.7,
            'sexual': 0.7,
            'self_harm': 0.6,
            'violence': 0.7,
            'drugs': 0.7,
            'threats': 0.7,
        }
        
        logger.info(f"✅ Decision Engine initialized with thresholds: {self.block_thresholds}")
        logger.info("ℹ️ Rule score interpretation: HIGH score (>0.5) means violations detected")
    
    def make_decision(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make moderation decision based on all inputs
        
        Args:
            inputs: Dictionary containing:
                - text_score: tech relevance (0-1)
                - toxicity_score: toxicity level (0-1)
                - sexual_score: sexual content (0-1)
                - self_harm_score: self-harm (0-1)
                - violence_score: violence (0-1)
                - drugs_score: drugs (0-1)
                - threats_score: threats (0-1)
                - rule_score: rule-based score (0-1) - HIGHER means more violations!
                - has_suspicious_urls: bool
                - is_harmful: bool from model
        """
        
        reasons = []
        
        # ── STEP 1: Check rule-based signals (fastest, most reliable) ──
        rule_score = inputs.get('rule_score', 0)
        if rule_score > 0.5:
            logger.warning(f"❌ BLOCKING due to rule engine: score={rule_score:.2f} > 0.5")
            return {
                "allowed": False,
                "reasons": ["rules"],
                "confidence": rule_score,
                "primary_category": "rules",
                "severity": "high",
                "score": rule_score
            }
        
        # Check for suspicious URLs
        if inputs.get('has_suspicious_urls', False):
            logger.warning(f"❌ BLOCKING due to suspicious URLs")
            return {
                "allowed": False,
                "reasons": ["suspicious_url"],
                "confidence": 0.8,
                "primary_category": "urls",
                "severity": "medium",
                "score": 0.8
            }
        
        # ── STEP 2: Special rule for tech content (only if rules didn't block) ──
        text_score = inputs.get('text_score', 0)
        if text_score > 0.6:
            harmful_scores = [
                inputs.get('toxicity_score', 0),
                inputs.get('sexual_score', 0),
                inputs.get('self_harm_score', 0),
                inputs.get('violence_score', 0),
                inputs.get('drugs_score', 0),
                inputs.get('threats_score', 0)
            ]
            avg_harmful = sum(harmful_scores) / len(harmful_scores) if harmful_scores else 0
            
            if avg_harmful < 0.5:
                logger.info(f"✅ ALLOWING tech content: score={text_score:.2f}, avg_harmful={avg_harmful:.2f}")
                return {
                    "allowed": True,
                    "reasons": ["tech_content"],
                    "confidence": text_score,
                    "primary_category": "tech",
                    "severity": "low",
                    "score": text_score
                }
        
        # ── STEP 3: Check each ML category against its threshold ──
        for category, threshold in self.block_thresholds.items():
            score_key = f"{category}_score"
            score = inputs.get(score_key, 0)
            
            if score > threshold:
                logger.warning(f"❌ BLOCKING due to {category}: {score:.2f} > {threshold}")
                return {
                    "allowed": False,
                    "reasons": [category],
                    "confidence": score,
                    "primary_category": category,
                    "severity": "high",
                    "score": score
                }
        
        # ── STEP 4: If nothing triggered, check if model says it's harmful ──
        if inputs.get('is_harmful', False):
            logger.warning(f"⚠️ Model indicates harmful but no threshold exceeded - safe block")
            return {
                "allowed": False,
                "reasons": ["harmful_content"],
                "confidence": 0.6,
                "primary_category": "flagged",
                "severity": "medium",
                "score": 0.6
            }
        
        # ── STEP 5: Default: allow if nothing triggered ──
        logger.info(f"✅ ALLOWING content: no violations detected")
        return {
            "allowed": True,
            "reasons": ["safe"],
            "confidence": 0.9,
            "primary_category": "safe",
            "severity": "low",
            "score": 0.9
        }