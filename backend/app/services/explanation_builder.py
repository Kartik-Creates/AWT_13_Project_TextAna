from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ExplanationBuilder:
    """Builds human-readable explanations for moderation decisions"""
    
    def __init__(self):
        self.templates = {
            # Rule-based
            "banned_keyword": "Banned keyword detected: {keywords}",
            "suspicious_url": "Suspicious URL detected: {urls}",
            "spam": "Content appears to be spam",
            "rules": "Content triggered safety rules",
            
            # Text-based categories
            "toxicity": "Toxic or harmful language detected",
            "sexual": "Sexual content detected",
            "self_harm": "Content related to self-harm or suicide detected",
            "violence": "Violent content detected",
            "drugs": "Drug-related content detected",
            "threats": "Threatening content detected",
            
            # Safe categories
            "tech_content": "✅ Technology content approved",
            "safe": "✅ No issues detected",
            "safe_content": "✅ Content approved"
        }
    
    def build_explanation(self, decision: Dict[str, Any], 
                          results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build explanation from decision and results
        Returns: Dict with reasons and flagged phrases
        """
        reasons = []
        flagged_phrases = []
        
        # Get decision reasons (these are just category names)
        decision_reasons = decision.get("reasons", [])
        
        for reason in decision_reasons:
            if reason in self.templates:
                reasons.append(self.templates[reason])
            else:
                reasons.append(reason)
        
        # Extract flagged phrases from rule engine
        if "rule_based" in results and results["rule_based"]:
            rule_results = results["rule_based"]
            if rule_results.get("banned_keywords"):
                flagged_phrases.extend(rule_results["banned_keywords"])
            if rule_results.get("suspicious_urls"):
                flagged_phrases.extend(rule_results["suspicious_urls"])
        
        # Remove duplicates
        flagged_phrases = list(set(filter(None, flagged_phrases)))
        
        return {
            "reasons": reasons,
            "flagged_phrases": flagged_phrases,
            "severity": decision.get("severity", "low"),
            "score": decision.get("score", 1.0)
        }
    
    def get_summary(self, reasons: List[str], allowed: bool = True) -> str:
        """Get a brief summary of why content was rejected"""
        if not reasons:
            return "Content approved" if allowed else "Content rejected"
        
        if len(reasons) == 1:
            return f"{'Approved' if allowed else 'Rejected'}: {reasons[0]}"
        
        return f"{'Approved' if allowed else 'Rejected'}: {len(reasons)} policy violations detected"