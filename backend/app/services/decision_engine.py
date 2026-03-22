"""
Decision Engine for Moderation System.

KEY CHANGE from previous version: The fast-allow shortcut has been removed.
High tech relevance score NEVER bypasses harm detection. Tech score only gates
off-topic content — harm checks always run for confirmed tech posts.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Makes final moderation decisions based on all signals.

    Decision flow:
      1. Rule-based harm check
      2. Suspicious URL check
      3. NSFW image check
      4. Tech relevance gate (blocks off-topic, never bypasses harm checks)
      5. Cyber-harm intent check (sandwich attack detection)
      6. ML harm category checks
      7. Generic is_harmful fallback
      8. Default allow
    """

    def __init__(self):
        self.block_thresholds = {
            'toxicity':  0.7,
            'sexual':    0.7,
            'self_harm': 0.6,
            'violence':  0.7,
            'drugs':     0.7,
            'threats':   0.7,
        }

        self.nsfw_threshold        = 0.6
        self.rule_threshold        = 0.6
        self.tech_block_threshold  = 0.20
        self.tech_review_threshold = 0.38
        self.cyber_harm_threshold  = 0.65

        logger.info("✅ Decision Engine initialized")
        logger.info(f"   Harm thresholds: {self.block_thresholds}")
        logger.info(f"   NSFW threshold: {self.nsfw_threshold}")
        logger.info(f"   Rule threshold: {self.rule_threshold}")
        logger.info(f"   Tech block threshold: {self.tech_block_threshold}")
        logger.info(f"   Tech review threshold: {self.tech_review_threshold}")
        logger.info(f"   Cyber-harm threshold: {self.cyber_harm_threshold}")

    def make_decision(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Make moderation decision based on all inputs.

        New inputs vs previous version:
          - cyber_harm_score        : float from TechContextFilter (0-1)
          - cyber_harm_category     : str category from intent filter
          - content_mixing_detected : bool from sentence mixing check
        """

        # ── STEP 1: Rule-based harm check ──────────────────────────────────
        rule_score = inputs.get('rule_score', 0)
        if rule_score > self.rule_threshold:
            logger.warning(f"❌ BLOCKING — rule engine: score={rule_score:.2f}")
            return {
                "allowed": False, "reasons": ["rules"],
                "confidence": rule_score, "primary_category": "rules",
                "severity": "high", "score": rule_score,
            }

        # ── STEP 2: Suspicious URL check ───────────────────────────────────
        if inputs.get('has_suspicious_urls', False):
            logger.warning("❌ BLOCKING — suspicious URLs")
            return {
                "allowed": False, "reasons": ["suspicious_url"],
                "confidence": 0.8, "primary_category": "urls",
                "severity": "medium", "score": 0.8,
            }

        # ── STEP 3: NSFW image check ────────────────────────────────────────
        nsfw_score = inputs.get('nsfw_score', 0)
        if nsfw_score > self.nsfw_threshold:
            logger.warning(f"❌ BLOCKING — NSFW image: {nsfw_score:.2f}")
            return {
                "allowed": False, "reasons": ["nsfw_image"],
                "confidence": nsfw_score, "primary_category": "nsfw",
                "severity": "high", "score": nsfw_score,
            }

        # ── STEP 4: Tech relevance gate ────────────────────────────────────
        tech_score = inputs.get('tech_relevance_score', inputs.get('text_score', 0))
        tech_zone  = inputs.get('tech_zone', self._infer_zone(tech_score))

        if tech_zone == "off_topic":
            logger.warning(f"❌ BLOCKING — off-topic: tech_score={tech_score:.3f}")
            return {
                "allowed": False, "reasons": ["off_topic"],
                "confidence": round(1.0 - tech_score, 3),
                "primary_category": "off_topic",
                "severity": "low", "score": round(1.0 - tech_score, 3),
            }

        if tech_zone == "review":
            logger.info(f"⚠️ REVIEW — ambiguous tech: tech_score={tech_score:.3f}")
            return {
                "allowed": False, "reasons": ["needs_review"],
                "confidence": round(1.0 - tech_score, 3),
                "primary_category": "review",
                "severity": "low", "score": round(1.0 - tech_score, 3),
            }

        # ── STEP 5: Cyber-harm intent (sandwich attack detection) ───────────
        cyber_harm_score    = inputs.get('cyber_harm_score', 0.0)
        cyber_harm_category = inputs.get('cyber_harm_category', '')
        content_mixing      = inputs.get('content_mixing_detected', False)

        if cyber_harm_score >= self.cyber_harm_threshold:
            logger.warning(
                f"❌ BLOCKING — cyber-harm intent: "
                f"score={cyber_harm_score:.3f} category={cyber_harm_category}"
            )
            return {
                "allowed": False, "reasons": ["cyber_harm_intent"],
                "confidence": cyber_harm_score,
                "primary_category": cyber_harm_category or "cyber_harm",
                "severity": "high", "score": cyber_harm_score,
            }

        if content_mixing:
            logger.warning("❌ BLOCKING — off-topic content mixed into tech post")
            return {
                "allowed": False, "reasons": ["content_mixing"],
                "confidence": 0.75, "primary_category": "content_mixing",
                "severity": "medium", "score": 0.75,
            }
        # ── CLIP image-text mismatch check ──
        clip_similarity = inputs.get('clip_similarity', None)
        if clip_similarity is not None and clip_similarity < 0.15:
            logger.warning(
                f"⚠️ REVIEW — image-text mismatch: "
                f"clip_similarity={clip_similarity:.4f}"
            )
            return {
                "allowed": False,
                "reasons": ["needs_review"],
                "confidence": round(1.0 - clip_similarity, 3),
                "primary_category": "image_mismatch",
                "severity": "low",
                "score": round(1.0 - clip_similarity, 3),
            }   

        # ── STEP 6: ML harm category checks ────────────────────────────────
        # Runs for ALL tech-zone posts — no fast-allow shortcut exists.
        for category, threshold in self.block_thresholds.items():
            score = inputs.get(f"{category}_score", 0)
            if score > threshold:
                logger.warning(f"❌ BLOCKING — {category}: {score:.2f}")
                return {
                    "allowed": False, "reasons": [category],
                    "confidence": score, "primary_category": category,
                    "severity": "high", "score": score,
                }

        # ── STEP 7: Generic harmful fallback ───────────────────────────────
        if inputs.get('is_harmful', False):
            logger.warning("⚠️ BLOCKING — model flagged harmful")
            return {
                "allowed": False, "reasons": ["harmful_content"],
                "confidence": 0.6, "primary_category": "flagged",
                "severity": "medium", "score": 0.6,
            }

        # ── STEP 8: Allow ───────────────────────────────────────────────────
        logger.info(f"✅ ALLOWING — tech content (tech_score={tech_score:.3f})")
        return {
            "allowed": True, "reasons": ["tech_content"],
            "confidence": tech_score, "primary_category": "tech",
            "severity": "low", "score": tech_score,
        }

    def _infer_zone(self, tech_score: float) -> str:
        if tech_score >= 0.38:   return "tech"
        elif tech_score >= 0.20: return "review"
        else:                    return "off_topic"
