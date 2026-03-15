import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DecisionEngine:
    """Makes final moderation decision by combining all analysis signals.
    
    Decision flow (any trigger → reject):
      1. Rule engine violations (keywords, URLs, spam)
      2. ML toxicity score from XLM-RoBERTa
      3. NSFW image detection
      4. Image-text relevance mismatch (CLIP)
    """
    
    def __init__(self):
        self.thresholds = {
            "toxicity": 0.45,       # XLM-RoBERTa sigmoid — 0.45 gives good recall
            "nsfw": 0.5,            # Falconsai binary classification
            "rule_score": 0.49,     # ≥1 keyword violation
            "relevance": 0.12,      # CLIP similarity below this = mismatch
        }
        
        # Categories that automatically reject regardless of score
        self.critical_categories = {
            "terrorism", "violence", "self_harm", "hate_speech",
            "discrimination", "sexual_content", "highly_toxic",
            "review_needed",
        }
    
    def make_decision(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Combine all analysis results into a single allow/reject decision."""
        decision = {
            "allowed": True,
            "reasons": [],
            "score": 1.0,
            "severity": "none",
        }
        
        if not results:
            return decision

        # ── 1. Rule Engine (keywords / URLs / spam) ──
        rules = results.get("rule_based") or {}
        rule_score = rules.get("rule_score", 0)
        
        if rule_score > self.thresholds["rule_score"]:
            decision["allowed"] = False
            if rules.get("banned_keywords"):
                decision["reasons"].append("banned_keyword")
            if rules.get("suspicious_urls"):
                decision["reasons"].append("suspicious_url")
            if rules.get("spam_detected"):
                decision["reasons"].append("spam")

        # ── 2. Text Analysis (XLM-RoBERTa) ──
        text = results.get("text_analysis") or {}
        if text:
            toxicity_score = text.get("toxicity_score", 0)
            category = text.get("category", "safe")
            is_toxic = text.get("is_toxic", False)
            
            # High toxicity score → reject
            if toxicity_score > self.thresholds["toxicity"] or is_toxic:
                decision["allowed"] = False
                decision["reasons"].append(category if category != "safe" else "toxicity")
            
            # Critical category → always reject
            if category in self.critical_categories:
                decision["allowed"] = False
                if category not in decision["reasons"]:
                    decision["reasons"].append(category)
            
            # Check individual flagged labels from multi-label model
            flagged_labels = text.get("flagged_labels", [])
            if flagged_labels:
                decision["allowed"] = False
                for label in flagged_labels:
                    mapped = self._map_label(label)
                    if mapped not in decision["reasons"]:
                        decision["reasons"].append(mapped)

        # ── 3. Image Analysis (NSFW) ──
        image = results.get("image_analysis") or {}
        if image:
            nsfw_prob = image.get("nsfw_probability", 0)
            if nsfw_prob > self.thresholds["nsfw"]:
                decision["allowed"] = False
                decision["reasons"].append("nsfw")
            if image.get("explicit_content_detected"):
                decision["allowed"] = False
                if "explicit" not in decision["reasons"]:
                    decision["reasons"].append("explicit")

        # ── 4. Image-Text Relevance (CLIP) ──
        relevance = results.get("relevance_analysis") or {}
        if relevance:
            sim_score = relevance.get("similarity_score", 1.0)
            if relevance.get("mismatch_detected") or sim_score < self.thresholds["relevance"]:
                decision["allowed"] = False
                if "mismatch" not in decision["reasons"]:
                    decision["reasons"].append("mismatch")

        # ── 5. URL Analysis ──
        url_analysis = results.get("url_analysis") or {}
        if url_analysis.get("has_suspicious_urls"):
            decision["allowed"] = False
            if "suspicious_url" not in decision["reasons"]:
                decision["reasons"].append("suspicious_url")

        # ── Final scoring ──
        if not decision["allowed"]:
            rule_s = rule_score
            text_s = text.get("toxicity_score", 0) if text else 0
            img_s = image.get("nsfw_probability", 0) if image else 0
            
            max_risk = max(rule_s, text_s, img_s)
            decision["score"] = round(1.0 - max_risk, 4)
            
            if max_risk > 0.8:
                decision["severity"] = "high"
            elif max_risk > 0.5:
                decision["severity"] = "medium"
            else:
                decision["severity"] = "low"
        
        # De-duplicate reasons
        decision["reasons"] = list(dict.fromkeys(decision["reasons"]))
        
        return decision
    
    @staticmethod
    def _map_label(label: str) -> str:
        """Map XLM-RoBERTa label names to decision reasons."""
        mapping = {
            "toxic": "toxicity",
            "severe_toxic": "highly_toxic",
            "obscene": "sexual_content",
            "threat": "violence",
            "insult": "hate_speech",
            "identity_hate": "discrimination",
        }
        return mapping.get(label, label)