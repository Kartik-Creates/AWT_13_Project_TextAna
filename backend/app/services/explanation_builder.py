from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ExplanationBuilder:
    """Builds human-readable explanations for moderation decisions"""
    
    def __init__(self):
        # Reason templates
        self.templates = {
            "banned_keyword": "Banned keyword detected: {keywords}",
            "suspicious_url": "Suspicious URL detected: {urls}",
            "spam": "Content appears to be spam",
            "toxicity": "Toxic or harmful language detected (score: {score:.2f})",
            "hate_speech": "Hate speech detected in content",
            "violence": "Violent content detected",
            "self_harm": "Content related to self-harm detected",
            "nsfw": "NSFW content detected in image (probability: {prob:.2f})",
            "explicit": "Explicit content detected",
            "mismatch": "Image content doesn't match the text description",
            "terrorism": "Content related to terrorism detected",
            "discrimination": "Discriminatory content detected"
        }
    
    def build_explanation(self, decision: Dict[str, Any], 
                          results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build explanation from decision and results
        Returns: Dict with reasons and flagged phrases
        """
        reasons = []
        flagged_phrases = []
        
        # Get decision reasons
        decision_reasons = decision.get("reasons", [])
        
        for reason in decision_reasons:
            explanation = self._format_reason(reason, results)
            if explanation:
                reasons.append(explanation)
        
        # Extract flagged phrases from results
        if "rule_based" in results:
            rule_results = results["rule_based"]
            if rule_results.get("banned_keywords"):
                flagged_phrases.extend(rule_results["banned_keywords"])
            if rule_results.get("suspicious_urls"):
                flagged_phrases.extend(rule_results["suspicious_urls"])
        
        if "text_analysis" in results:
            text_results = results["text_analysis"]
            if text_results.get("flagged_phrases"):
                for phrase in text_results["flagged_phrases"]:
                    if isinstance(phrase, dict):
                        flagged_phrases.append(phrase.get("phrase", ""))
                    else:
                        flagged_phrases.append(phrase)
        
        # Remove duplicates
        flagged_phrases = list(set(filter(None, flagged_phrases)))
        
        return {
            "reasons": reasons,
            "flagged_phrases": flagged_phrases,
            "severity": decision.get("severity", "unknown"),
            "score": decision.get("score", 1.0)
        }
    
    def _format_reason(self, reason: str, results: Dict[str, Any]) -> str:
        """Format a specific reason with details"""
        
        if reason in self.templates:
            template = self.templates[reason]
            
            # Add details based on reason type
            if reason == "banned_keyword" and "rule_based" in results:
                keywords = results["rule_based"].get("banned_keywords", [])
                return template.format(keywords=", ".join(keywords))
            
            elif reason == "suspicious_url" and "rule_based" in results:
                urls = results["rule_based"].get("suspicious_urls", [])
                return template.format(urls=", ".join(urls))
            
            elif reason == "toxicity" and "text_analysis" in results:
                score = results["text_analysis"].get("toxicity_score", 0)
                return template.format(score=score)
            
            elif reason == "nsfw" and "image_analysis" in results:
                prob = results["image_analysis"].get("nsfw_probability", 0)
                return template.format(prob=prob)
            
            else:
                return template
            
        return reason
    
    def get_summary(self, reasons: List[str]) -> str:
        """Get a brief summary of why content was rejected"""
        if not reasons:
            return "Content approved"
        
        if len(reasons) == 1:
            return f"Rejected: {reasons[0]}"
        
        return f"Rejected: {len(reasons)} policy violations detected"