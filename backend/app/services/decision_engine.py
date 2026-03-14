from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DecisionEngine:
    """Makes final decision on content based on all analysis"""
    
    def __init__(self):
        # Decision thresholds
        self.thresholds = {
            "toxicity": 0.7,
            "nsfw": 0.7,
            "rule_violations": 3,  # Number of rule violations
            "relevance": 0.2  # Minimum relevance score
        }
        
        # Rejection reasons mapping
        self.rejection_reasons = {
            "toxicity": "Content contains toxic or harmful language",
            "nsfw": "Image contains NSFW or explicit content",
            "hate_speech": "Content contains hate speech",
            "violence": "Content promotes violence",
            "self_harm": "Content related to self-harm",
            "spam": "Content appears to be spam",
            "suspicious_url": "Contains suspicious URL",
            "banned_keyword": "Contains banned keywords",
            "mismatch": "Image content doesn't match text",
            "explicit": "Explicit content detected"
        }
    
    def make_decision(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make final moderation decision
        Returns: Dict with decision and reasons
        """
        decision = {
            "allowed": True,
            "reasons": [],
            "score": 1.0,
            "severity": "low"
        }
        
        # Check rule-based violations
        if "rule_based" in results:
            rule_results = results["rule_based"]
            
            # Check banned keywords
            if rule_results.get("banned_keywords"):
                decision["allowed"] = False
                decision["reasons"].append("banned_keyword")
            
            # Check suspicious URLs
            if rule_results.get("suspicious_urls"):
                decision["allowed"] = False
                decision["reasons"].append("suspicious_url")
            
            # Check spam
            if rule_results.get("spam_detected"):
                decision["allowed"] = False
                decision["reasons"].append("spam")
        
        # Check text analysis
        if "text_analysis" in results:
            text_results = results["text_analysis"]
            
            # Check toxicity
            if text_results.get("is_toxic", False):
                decision["allowed"] = False
                decision["reasons"].append(text_results.get("category", "toxicity"))
            
            # Check category-specific violations
            category = text_results.get("category", "safe")
            if category in ["hate_speech", "violence", "self_harm", "terrorism"]:
                decision["allowed"] = False
                decision["reasons"].append(category)
        
        # Check image analysis
        if "image_analysis" in results:
            image_results = results["image_analysis"]
            
            # Check NSFW
            if image_results.get("is_nsfw", False):
                decision["allowed"] = False
                decision["reasons"].append("nsfw")
            
            # Check explicit content
            if image_results.get("explicit_content_detected", False):
                decision["allowed"] = False
                decision["reasons"].append("explicit")
        
        # Check relevance
        if "relevance_analysis" in results:
            relevance = results["relevance_analysis"]
            
            # Check mismatch
            if relevance.get("mismatch_detected", False):
                decision["allowed"] = False
                decision["reasons"].append("mismatch")
        
        # Calculate overall score (0-1, higher means more likely to be allowed)
        if decision["reasons"]:
            # Start with base score
            score = 1.0
            
            # Reduce score based on number of reasons
            score -= len(decision["reasons"]) * 0.2
            
            # Further reduce based on severity
            severity_weights = {
                "hate_speech": 0.3,
                "violence": 0.3,
                "terrorism": 0.4,
                "nsfw": 0.25,
                "explicit": 0.25,
                "self_harm": 0.3,
                "suspicious_url": 0.2
            }
            
            for reason in decision["reasons"]:
                if reason in severity_weights:
                    score -= severity_weights[reason]
            
            decision["score"] = max(0, score)
            
            # Determine severity
            if decision["score"] < 0.3:
                decision["severity"] = "high"
            elif decision["score"] < 0.6:
                decision["severity"] = "medium"
            else:
                decision["severity"] = "low"
        else:
            decision["score"] = 1.0
            decision["severity"] = "none"
        
        return decision