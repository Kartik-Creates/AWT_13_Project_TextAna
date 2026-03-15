import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DecisionEngine:
    """Makes final decision on content based on all analysis"""
    
    def __init__(self):
        # Professional thresholds (0.7 is the industry standard for probability models)
        self.thresholds = {
            "toxicity": 0.7,
            "nsfw": 0.7,
            "rule_score": 0.49, # Block if rule_score > 0.49 (i.e., at least 1 violation)
            "relevance": 0.15
        }
    
    def make_decision(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine all analyses into a single decision.
        """
        decision = {
            "allowed": True,
            "reasons": [],
            "score": 1.0,
            "severity": "low"
        }
        
        if not results:
            return decision

        # 1. Check Rule Engine (Keywords/URLs/Spam)
        rules = results.get("rule_based", {})
        if rules.get("rule_score", 0) > self.thresholds["rule_score"]:
            decision["allowed"] = False
            if rules.get("banned_keywords"):
                decision["reasons"].append("banned_keyword")
            if rules.get("suspicious_urls"):
                decision["reasons"].append("suspicious_url")
            if rules.get("spam_detected"):
                decision["reasons"].append("spam")

        # 2. Check Text Analysis (DistilBERT)
        text = results.get("text_analysis", {})
        if text:
            # Check toxicity score
            if text.get("toxicity_score", 0) > self.thresholds["toxicity"]:
                decision["allowed"] = False
                decision["reasons"].append(text.get("category", "toxicity"))
            
            # Critical categories automatically block
            if text.get("category") in ["terrorism", "self_harm", "hate_speech"]:
                decision["allowed"] = False
                decision["reasons"].append(text["category"])

        # 3. Check Image Analysis (NSFW)
        image = results.get("image_analysis", {})
        if image:
            if image.get("nsfw_probability", 0) > self.thresholds["nsfw"]:
                decision["allowed"] = False
                decision["reasons"].append("nsfw")
            if image.get("explicit_content_detected"):
                decision["allowed"] = False
                decision["reasons"].append("explicit")

        # Final Score Calculation
        if not decision["allowed"]:
            # If rejected, score is based on the highest risk factor found
            rule_s = rules.get("rule_score", 0)
            text_s = text.get("toxicity_score", 0) if text else 0
            img_s = image.get("nsfw_probability", 0) if image else 0
            
            max_risk = max(rule_s, text_s, img_s)
            decision["score"] = 1.0 - max_risk
            
            # Determine Severity
            if max_risk > 0.9:
                decision["severity"] = "high"
            elif max_risk > 0.6:
                decision["severity"] = "medium"
            else:
                decision["severity"] = "low"
        else:
            decision["score"] = 1.0
            decision["severity"] = "none"

        return decision