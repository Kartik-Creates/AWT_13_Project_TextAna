"""
Decision Engine for Moderation System
"""
 
import logging
from typing import Dict, Any
 
logger = logging.getLogger(__name__)
 
class DecisionEngine:
    """Makes final moderation decisions based on all signals.
 
    Decision flow:
      1. Rule-based harm check (fast exit for clear violations)
      2. Suspicious URL check
      3. NSFW image check
      4. Tech relevance gate  ← NEW: blocks off-topic content
      5. ML harm category checks
      6. Generic is_harmful fallback
      7. Default allow
    """
 
    def __init__(self):
        # Thresholds for blocking harmful content
        self.block_thresholds = {
            'toxicity': 0.7,
            'sexual': 0.7,
            'self_harm': 0.6,
            'violence': 0.7,
            'drugs': 0.7,
            'threats': 0.7,
        }
 
        # NSFW image threshold
        self.nsfw_threshold = 0.6
 
        # Rule engine harm threshold
        self.rule_threshold = 0.6
 
        # Tech relevance thresholds
        # Posts below BLOCK_THRESHOLD are definitely off-topic → blocked
        # Posts between BLOCK_THRESHOLD and REVIEW_THRESHOLD → sent to review
        # Posts above REVIEW_THRESHOLD → allowed through to harm checks
        self.tech_block_threshold = 0.25   # below this → off_topic block
        self.tech_review_threshold = 0.45  # below this → review queue
 
        logger.info(f"✅ Decision Engine initialized")
        logger.info(f"   Harm thresholds: {self.block_thresholds}")
        logger.info(f"   NSFW threshold: {self.nsfw_threshold}")
        logger.info(f"   Rule threshold: {self.rule_threshold}")
        logger.info(f"   Tech block threshold: {self.tech_block_threshold}")
        logger.info(f"   Tech review threshold: {self.tech_review_threshold}")
 
    def make_decision(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make moderation decision based on all inputs.
 
        Args:
            inputs: Dictionary containing:
                - rule_score           : float  — rule-based harm score (0–1, higher = worse)
                - has_suspicious_urls  : bool
                - nsfw_score           : float  — NSFW probability from image (0–1)
                - tech_relevance_score : float  — tech relevance (0–1, higher = more tech)  ← NEW
                - tech_zone            : str    — "tech" | "review" | "off_topic"           ← NEW
                - text_score           : float  — alias for tech_relevance (legacy)
                - toxicity_score       : float
                - sexual_score         : float
                - self_harm_score      : float
                - violence_score       : float
                - drugs_score          : float
                - threats_score        : float
                - is_harmful           : bool   — model-level harmful flag
 
        Returns:
            Dict with: allowed, reasons, confidence, primary_category, severity, score
        """
 
        # ── STEP 1: Rule-based harm check (fastest exit) ──
        rule_score = inputs.get('rule_score', 0)
        if rule_score > self.rule_threshold:
            logger.warning(
                f"❌ BLOCKING — rule engine: score={rule_score:.2f} > {self.rule_threshold}"
            )
            return {
                "allowed": False,
                "reasons": ["rules"],
                "confidence": rule_score,
                "primary_category": "rules",
                "severity": "high",
                "score": rule_score
            }
 
        # ── STEP 2: Suspicious URL check ──
        if inputs.get('has_suspicious_urls', False):
            logger.warning("❌ BLOCKING — suspicious URLs detected")
            return {
                "allowed": False,
                "reasons": ["suspicious_url"],
                "confidence": 0.8,
                "primary_category": "urls",
                "severity": "medium",
                "score": 0.8
            }
 
        # ── STEP 3: NSFW image check ──
        nsfw_score = inputs.get('nsfw_score', 0)
        if nsfw_score > self.nsfw_threshold:
            logger.warning(
                f"❌ BLOCKING — NSFW image: {nsfw_score:.2f} > {self.nsfw_threshold}"
            )
            return {
                "allowed": False,
                "reasons": ["nsfw_image"],
                "confidence": nsfw_score,
                "primary_category": "nsfw",
                "severity": "high",
                "score": nsfw_score
            }
 
        # ── STEP 4: Tech relevance gate ──
        # Use tech_relevance_score if available, fall back to text_score for backwards compatibility
        tech_score = inputs.get('tech_relevance_score', inputs.get('text_score', 0))
        tech_zone = inputs.get('tech_zone', self._infer_zone(tech_score))
 
        if tech_zone == "off_topic":
            logger.warning(
                f"❌ BLOCKING — off-topic content: tech_score={tech_score:.3f} < {self.tech_block_threshold}"
            )
            return {
                "allowed": False,
                "reasons": ["off_topic"],
                "confidence": round(1.0 - tech_score, 3),
                "primary_category": "off_topic",
                "severity": "low",
                "score": round(1.0 - tech_score, 3)
            }
 
        if tech_zone == "review":
            logger.info(
                f"⚠️ REVIEW — ambiguous tech relevance: tech_score={tech_score:.3f}"
            )
            return {
                "allowed": False,
                "reasons": ["needs_review"],
                "confidence": round(1.0 - tech_score, 3),
                "primary_category": "review",
                "severity": "low",
                "score": round(1.0 - tech_score, 3)
            }
 
        # ── STEP 5: Fast-allow clearly safe tech content ──
        # If tech relevance is high and no significant harm signals, allow immediately
        if tech_score >= 0.65:
            harmful_scores = [
                inputs.get('toxicity_score', 0),
                inputs.get('sexual_score', 0),
                inputs.get('self_harm_score', 0),
                inputs.get('violence_score', 0),
                inputs.get('drugs_score', 0),
                inputs.get('threats_score', 0)
            ]
            avg_harmful = sum(harmful_scores) / len(harmful_scores) if harmful_scores else 0
            max_harmful = max(harmful_scores) if harmful_scores else 0
 
            if avg_harmful < 0.3 and max_harmful < 0.5:
                logger.info(
                    f"✅ ALLOWING — strong tech content: score={tech_score:.3f}, "
                    f"avg_harm={avg_harmful:.3f}, max_harm={max_harmful:.3f}"
                )
                return {
                    "allowed": True,
                    "reasons": ["tech_content"],
                    "confidence": tech_score,
                    "primary_category": "tech",
                    "severity": "low",
                    "score": tech_score
                }
 
        # ── STEP 6: ML harm category checks ──
        for category, threshold in self.block_thresholds.items():
            score_key = f"{category}_score"
            score = inputs.get(score_key, 0)
 
            if score > threshold:
                logger.warning(
                    f"❌ BLOCKING — {category}: {score:.2f} > {threshold}"
                )
                return {
                    "allowed": False,
                    "reasons": [category],
                    "confidence": score,
                    "primary_category": category,
                    "severity": "high",
                    "score": score
                }
 
        # ── STEP 7: Generic harmful flag fallback ──
        if inputs.get('is_harmful', False):
            logger.warning("⚠️ BLOCKING — model flagged as harmful (no threshold exceeded)")
            return {
                "allowed": False,
                "reasons": ["harmful_content"],
                "confidence": 0.6,
                "primary_category": "flagged",
                "severity": "medium",
                "score": 0.6
            }
 
        # ── STEP 8: Default allow ──
        logger.info("✅ ALLOWING — no violations detected")
        return {
            "allowed": True,
            "reasons": ["safe"],
            "confidence": 0.9,
            "primary_category": "safe",
            "severity": "low",
            "score": 0.9
        }
 
    def _infer_zone(self, tech_score: float) -> str:
        """Infer zone from score when tech_zone is not explicitly provided."""
        if tech_score >= 0.45:
            return "tech"
        elif tech_score >= 0.25:
            return "review"
        else:
            return "off_topic"
 