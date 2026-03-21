"""
Decision Engine for Moderation System
Enhanced with stricter URL blocking
"""

import logging
from typing import Dict, Any, List, Optional

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
        
        # URL-specific thresholds - STRICTER
        self.url_thresholds = {
            'high_risk': 0.5,        # LOWERED from 0.7 to 0.5
            'medium_risk': 0.3,      # LOWERED from 0.4 to 0.3
            'shortened_url': 0.4,    # Any shortened URL with score > 0.4 = BLOCK
            'max_safe_risk': 0.2,    # URLs above this are considered suspicious
            'scam_keywords': 0.3,    # URLs with scam keywords get lower threshold
        }
        
        # Scam/phishing keywords in URLs
        self.scam_url_keywords = [
            'free', 'bonus', 'prize', 'winner', 'claim', 'gift', 'reward',
            'cash', 'money', 'lottery', 'jackpot', 'offer', 'limited',
            'congratulations', 'won', 'click', 'earn', 'quick', 'easy'
        ]
        
        # NSFW threshold
        self.nsfw_threshold = 0.6
        
        # Rule score threshold
        self.rule_threshold = 0.5  # LOWERED from 0.6 to 0.5
        
        logger.info(f"✅ Decision Engine initialized with stricter thresholds: {self.block_thresholds}")
        logger.info(f"✅ URL thresholds: {self.url_thresholds}")
        logger.info(f"✅ Scam URL keywords: {self.scam_url_keywords}")
        logger.info(f"✅ NSFW threshold: {self.nsfw_threshold}")
        logger.info(f"✅ Rule score threshold: {self.rule_threshold}")
    
    def _check_url_for_scam_patterns(self, url: str) -> float:
        """Check if URL contains scam/phishing patterns"""
        url_lower = url.lower()
        scam_score = 0.0
        
        for keyword in self.scam_url_keywords:
            if keyword in url_lower:
                scam_score += 0.15  # Add 0.15 per scam keyword
        
        return min(scam_score, 0.8)  # Cap at 0.8
    
    def make_decision(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make moderation decision based on all inputs with STRICT URL handling
        """
        
        reasons = []
        url_summary = inputs.get('url_summary', {})
        url_analysis = inputs.get('url_analysis', [])
        
        # ── STEP 1: Check URL risk levels (HIGHEST PRIORITY) ──
        has_high_risk_url = False
        has_medium_risk_url = False
        has_shortened_url = False
        has_scam_url = False
        high_risk_urls = []
        medium_risk_urls = []
        scam_urls = []
        
        for url_info in url_analysis:
            risk_score = url_info.get('risk_score', 0)
            risk_level = url_info.get('risk_level', 'SAFE')
            full_url = url_info.get('full_url', '')
            
            # Check for scam patterns in URL
            scam_score = self._check_url_for_scam_patterns(full_url)
            if scam_score > 0.3:
                has_scam_url = True
                scam_urls.append(full_url)
                # Boost risk score for scam patterns
                risk_score = max(risk_score, scam_score)
                url_info['risk_score'] = risk_score
                logger.warning(f"🚨 Scam pattern detected in URL: {full_url} (scam_score={scam_score:.2f})")
            
            # Check for shortened URLs
            if url_info.get('is_shortened', False):
                has_shortened_url = True
                # Boost risk for shortened URLs
                risk_score = max(risk_score, 0.4)
                url_info['risk_score'] = risk_score
            
            # Determine risk level with lower thresholds
            if risk_score >= self.url_thresholds['high_risk']:
                has_high_risk_url = True
                high_risk_urls.append(full_url)
                reasons.append(f"high_risk_url")
            elif risk_score >= self.url_thresholds['medium_risk']:
                has_medium_risk_url = True
                medium_risk_urls.append(full_url)
        
        # Block ANY URL with scam patterns, shortened URLs, or medium/high risk
        if has_scam_url:
            logger.warning(f"❌ BLOCKING due to scam URL patterns: {scam_urls}")
            return {
                "allowed": False,
                "reasons": ["scam_url_pattern"] + reasons,
                "confidence": 0.9,
                "primary_category": "scam_url",
                "severity": "high",
                "score": 0.9,
                "url_details": {
                    "high_risk_urls": high_risk_urls,
                    "medium_risk_urls": medium_risk_urls,
                    "scam_urls": scam_urls
                }
            }
        
        # Block high-risk URLs immediately (now threshold 0.5)
        if has_high_risk_url:
            logger.warning(f"❌ BLOCKING due to high-risk URL(s): {len(high_risk_urls)} URLs with risk >= {self.url_thresholds['high_risk']}")
            return {
                "allowed": False,
                "reasons": ["high_risk_url"] + reasons,
                "confidence": 0.9,
                "primary_category": "urls",
                "severity": "high",
                "score": 0.9,
                "url_details": {
                    "high_risk_urls": high_risk_urls,
                    "medium_risk_urls": medium_risk_urls
                }
            }
        
        # Block shortened URLs even with medium risk
        if has_shortened_url and has_medium_risk_url:
            logger.warning(f"❌ BLOCKING due to shortened URL with medium risk")
            return {
                "allowed": False,
                "reasons": ["shortened_url", "suspicious_url"] + reasons,
                "confidence": 0.85,
                "primary_category": "urls",
                "severity": "high",
                "score": 0.85,
                "url_details": {
                    "high_risk_urls": high_risk_urls,
                    "medium_risk_urls": medium_risk_urls
                }
            }
        
        # Block ANY shortened URL that also has spam/promotional content
        if has_shortened_url:
            rule_score = inputs.get('rule_score', 0)
            if rule_score > 0.2:  # Any rule violation + shortened URL = BLOCK
                logger.warning(f"❌ BLOCKING due to shortened URL + rule violations")
                return {
                    "allowed": False,
                    "reasons": ["shortened_url", "combined_violations"] + reasons,
                    "confidence": 0.8,
                    "primary_category": "urls",
                    "severity": "high",
                    "score": 0.8,
                    "url_details": {
                        "high_risk_urls": high_risk_urls,
                        "medium_risk_urls": medium_risk_urls
                    }
                }
        
        # ── STEP 2: Check rule-based signals (with lower threshold) ──
        rule_score = inputs.get('rule_score', 0)
        if rule_score > self.rule_threshold:
            logger.warning(f"❌ BLOCKING due to rule engine: score={rule_score:.2f} > {self.rule_threshold}")
            return {
                "allowed": False,
                "reasons": ["rules"] + reasons,
                "confidence": rule_score,
                "primary_category": "rules",
                "severity": "high",
                "score": rule_score,
                "url_details": {
                    "high_risk_urls": high_risk_urls,
                    "medium_risk_urls": medium_risk_urls
                }
            }
        
        # ── STEP 3: Check for suspicious URLs with context ──
        has_suspicious_urls = inputs.get('has_suspicious_urls', False)
        if has_suspicious_urls:
            # Block suspicious URLs even without other violations
            logger.warning(f"❌ BLOCKING due to suspicious URLs (strict mode)")
            return {
                "allowed": False,
                "reasons": ["suspicious_url"] + reasons,
                "confidence": 0.75,
                "primary_category": "urls",
                "severity": "medium",
                "score": 0.75,
                "url_details": {
                    "high_risk_urls": high_risk_urls,
                    "medium_risk_urls": medium_risk_urls
                }
            }
        
        # ── STEP 4: Check NSFW from images (if available) ──
        nsfw_score = inputs.get('nsfw_score', 0)
        if nsfw_score > self.nsfw_threshold:
            logger.warning(f"❌ BLOCKING due to NSFW image: {nsfw_score:.2f} > {self.nsfw_threshold}")
            return {
                "allowed": False,
                "reasons": ["nsfw_image"] + reasons,
                "confidence": nsfw_score,
                "primary_category": "nsfw",
                "severity": "high",
                "score": nsfw_score,
                "url_details": {
                    "high_risk_urls": high_risk_urls,
                    "medium_risk_urls": medium_risk_urls
                }
            }
        
        # ── STEP 5: Special rule for tech content - WITH URL EXCEPTION ──
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
            
            # Even tech content should be blocked if it has suspicious URLs
            if has_suspicious_urls or has_shortened_url:
                logger.warning(f"❌ BLOCKING tech content with suspicious URLs")
                return {
                    "allowed": False,
                    "reasons": ["tech_content_with_suspicious_url"] + reasons,
                    "confidence": 0.7,
                    "primary_category": "urls",
                    "severity": "medium",
                    "score": 0.7,
                    "url_details": {
                        "high_risk_urls": high_risk_urls,
                        "medium_risk_urls": medium_risk_urls
                    }
                }
            
            if avg_harmful < 0.5:
                logger.info(f"✅ ALLOWING tech content: score={text_score:.2f}, avg_harmful={avg_harmful:.2f}")
                return {
                    "allowed": True,
                    "reasons": ["tech_content"],
                    "confidence": text_score,
                    "primary_category": "tech",
                    "severity": "low",
                    "score": text_score,
                }
        
        # ── STEP 6: Check each ML category against its threshold ──
        for category, threshold in self.block_thresholds.items():
            score_key = f"{category}_score"
            score = inputs.get(score_key, 0)
            
            if score > threshold:
                logger.warning(f"❌ BLOCKING due to {category}: {score:.2f} > {threshold}")
                return {
                    "allowed": False,
                    "reasons": [category] + reasons,
                    "confidence": score,
                    "primary_category": category,
                    "severity": "high",
                    "score": score,
                    "url_details": {
                        "high_risk_urls": high_risk_urls,
                        "medium_risk_urls": medium_risk_urls
                    }
                }
        
        # ── STEP 7: If nothing triggered, check if model says it's harmful ──
        if inputs.get('is_harmful', False):
            logger.warning(f"⚠️ Model indicates harmful but no threshold exceeded - safe block")
            return {
                "allowed": False,
                "reasons": ["harmful_content"] + reasons,
                "confidence": 0.6,
                "primary_category": "flagged",
                "severity": "medium",
                "score": 0.6,
                "url_details": {
                    "high_risk_urls": high_risk_urls,
                    "medium_risk_urls": medium_risk_urls
                }
            }
        
        # ── STEP 8: Default: allow if nothing triggered ──
        logger.info(f"✅ ALLOWING content: no violations detected")
        return {
            "allowed": True,
            "reasons": ["safe"],
            "confidence": 0.9,
            "primary_category": "safe",
            "severity": "low",
            "score": 0.9,
        }
    
    def get_decision_summary(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Get a human-readable summary of the decision"""
        summary = {
            "action": "ALLOW" if decision.get("allowed", True) else "BLOCK",
            "reasons": decision.get("reasons", []),
            "severity": decision.get("severity", "low"),
            "confidence": f"{decision.get('confidence', 0)*100:.0f}%",
            "primary_category": decision.get("primary_category", "safe")
        }
        
        if decision.get("warning"):
            summary["warning"] = decision["warning"]
        
        if decision.get("url_details"):
            url_details = decision["url_details"]
            if url_details.get("high_risk_urls"):
                summary["high_risk_urls"] = len(url_details["high_risk_urls"])
            if url_details.get("medium_risk_urls"):
                summary["medium_risk_urls"] = len(url_details["medium_risk_urls"])
            if url_details.get("scam_urls"):
                summary["scam_urls"] = len(url_details["scam_urls"])
        
        return summary

# Global instance
decision_engine = DecisionEngine()