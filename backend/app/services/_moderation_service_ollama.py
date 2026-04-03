"""
Moderation Service - Orchestrates the entire moderation pipeline
Uses Ollama for text moderation
"""

from typing import Optional, Dict, Any, List
import asyncio
import logging
import os
import sys
from datetime import datetime
from functools import partial

from app.services.rule_engine import RuleEngine
from app.services.text_processor import TextProcessor
from app.services.decision_engine import DecisionEngine
from app.services.explanation_builder import ExplanationBuilder
from app.services.url_extractor import url_extractor
from app.ml.clip_model import clip_analyzer
from app.ml.efficientnet_model import efficientnet_nsfw as nsfw_detector
from app.ml.ollama_moderator import get_ollama_moderator
from app.db.mongodb import post_repository

logger = logging.getLogger(__name__)

print("🔥 MODERATION SERVICE LOADING...")
sys.stdout.flush()


class ModerationService:
    def __init__(self):
        self.rule_engine = RuleEngine()
        self.text_processor = TextProcessor()
        self.decision_engine = DecisionEngine()
        self.explanation_builder = ExplanationBuilder()
        logger.info("✅ Moderation service initialized")
        print("🔥 MODERATION SERVICE INITIALIZED")
        sys.stdout.flush()

    async def _run_sync(self, func, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

    # ── ADDED: Borderline detection for human review ──
    def _is_borderline(self, decision_input: dict) -> tuple[bool, list]:
        """Flag posts that are borderline for human review.
        Triggers when: tech relevance is in review zone OR models disagree.
        """
        reasons = []
        tech = decision_input.get('text_score', 0)
        tox  = decision_input.get('toxicity_score', 0)
        rule = decision_input.get('rule_score', 0)

        # Condition 1: tech relevance in review zone
        if 0.3 <= tech <= 0.5:
            reasons.append(f"Tech relevance in review zone: {tech:.2f}")

        # Condition 2: rule engine and toxicity model disagree
        if rule < 0.4 and tox > 0.4:
            reasons.append(f"Models disagree — rule_score={rule:.2f}, toxicity={tox:.2f}")

        return len(reasons) > 0, reasons
    # ── END ADDED ──

    async def moderate_post(
        self,
        post_id: str,
        text: str,
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        print(f"🔥🔥🔥 MODERATION CALLED: post_id={post_id}, text='{text[:100] if text else 'EMPTY'}'")
        sys.stdout.flush()
        logger.info(f"▶️ Starting moderation — post: {post_id}")

        try:
            # Step 1: Rule-based checks
            rule_results = self.rule_engine.check_rules(text)
            print(f"🔥 Rule score: {rule_results.get('rule_score', 0):.2f}")
            sys.stdout.flush()

            # Step 2: URL extraction
            urls = url_extractor.extract_urls(text)
            suspicious_urls = [u for u in urls if u.get("risk_level") in ("MEDIUM", "HIGH")]

            # Step 3: Mixing detection
            tech_relevance = self.rule_engine.check_tech_relevance(text)
            mixing_detected = tech_relevance.get('mixing', {}).get('mixing_detected', False)
            matched_terms = tech_relevance.get('matched_terms', [])
            
            print(f"🔥 Mixing detected: {mixing_detected}, matched terms: {matched_terms}")
            sys.stdout.flush()

            # Early exit for high rule score
            if rule_results.get('rule_score', 0) > 0.8:
                logger.warning(f"🛑 EARLY BLOCK by rule engine")
                return {"post_id": post_id, "allowed": False, "results": {"block_reason": "rule_engine"}}

            # Step 4: OLLAMA TEXT ANALYSIS
            try:
                print("🔥 Calling Ollama...")
                sys.stdout.flush()
                model = get_ollama_moderator()
                text_results = await self._run_sync(model.analyze, text)
                print(f"🔥 Ollama result: tech={text_results.get('scores', {}).get('tech_relevance', 'N/A')}")
                sys.stdout.flush()
                logger.info("✅ Ollama text analysis complete")
            except Exception as e:
                print(f"🔥 Ollama failed: {e}")
                sys.stdout.flush()
                text_results = {
                    "scores": {"tech_relevance": 0.5, "toxicity": 0, "sexual": 0, "self_harm": 0,
                               "violence": 0, "drugs": 0, "threats": 0},
                    "flagged_categories": [],
                    "is_harmful": False,
                    "is_tech_relevant": False,
                    "primary_category": "safe",
                    "tech_zone": "review"
                }

            # Step 5: Image analysis
            nsfw_score = 0.0
            if image_path:
                clean_path = image_path.lstrip('/')
                full_image_path = os.path.normpath(clean_path)
                if os.path.exists(full_image_path):
                    try:
                        nsfw_results = await self._run_sync(nsfw_detector.analyze, full_image_path)
                        nsfw_score = nsfw_results.get('nsfw_probability', 0)
                        logger.info(f"🖼️ NSFW: prob={nsfw_score:.4f}")
                    except Exception as e:
                        logger.error(f"NSFW failed: {e}")
                    
                    try:
                        clip_results = await self._run_sync(clip_analyzer.analyze, text, full_image_path)
                        logger.info(f"🔄 CLIP: similarity={clip_results.get('similarity_score', 0):.4f}")
                    except Exception as e:
                        logger.error(f"CLIP failed: {e}")

            # Step 6: Build decision input
            text_scores = text_results.get('scores', {})
            decision_input = {
                'rule_score': rule_results.get('rule_score', 0.0),
                'has_suspicious_urls': len(suspicious_urls) > 0,
                'is_harmful': text_results.get('is_harmful', False),
                'nsfw_score': nsfw_score,
                'text_score': text_scores.get('tech_relevance', 0.5),
                'tech_zone': text_results.get('tech_zone', 'review'),
                'matched_terms': matched_terms,
                'content_mixing_detected': mixing_detected,
                'toxicity_score': text_scores.get('toxicity', 0.0),
                'sexual_score': text_scores.get('sexual', 0.0),
                'self_harm_score': text_scores.get('self_harm', 0.0),
                'violence_score': text_scores.get('violence', 0.0),
                'drugs_score': text_scores.get('drugs', 0.0),
                'threats_score': text_scores.get('threats', 0.0),
            }

            print(f"🔥 Decision input: text_score={decision_input['text_score']:.3f}")
            sys.stdout.flush()

            # ── ADDED: Borderline check — flag for human review before final decision ──
            is_borderline, review_reasons = self._is_borderline(decision_input)
            if is_borderline and not decision_input.get('is_harmful'):
                logger.info(f"🔍 HUMAN REVIEW: Post {post_id} flagged as borderline — {review_reasons}")
                post_repository.flag_for_human_review(
                    post_id=post_id,
                    reasons=review_reasons,
                    scores={k: v for k, v in decision_input.items() if isinstance(v, float)}
                )
                return {
                    "post_id": post_id,
                    "allowed": True,
                    "human_review": True,
                    "review_reasons": review_reasons,
                }
            # ── END ADDED ──

            # Step 7: Decision
            decision = self.decision_engine.make_decision(decision_input)
            explanation = self.explanation_builder.build_explanation(decision, {})

            # Step 8: Update DB
            post_repository.update_moderation_result(
                post_id=post_id,
                allowed=decision["allowed"],
                reasons=explanation.get("reasons", []),
                flagged_phrases=explanation.get("flagged_phrases", []),
            )

            print(f"🔥 FINAL DECISION: {'ALLOWED' if decision['allowed'] else 'BLOCKED'}")
            sys.stdout.flush()
            logger.info(f"✅ Moderation complete — post={post_id}, allowed={decision['allowed']}")

            return {
                "post_id": post_id,
                "allowed": decision["allowed"],
                "results": {},
            }

        except Exception as e:
            print(f"🔥 PIPELINE ERROR: {e}")
            sys.stdout.flush()
            logger.error(f"❌ Pipeline error: {e}", exc_info=True)
            return {"post_id": post_id, "allowed": False, "error": str(e)}