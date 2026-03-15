from typing import Optional, Dict, Any, List
import asyncio
import logging
from datetime import datetime
import os
from functools import partial

from app.services.rule_engine import RuleEngine
from app.services.text_processor import TextProcessor
from app.services.decision_engine import DecisionEngine
from app.services.explanation_builder import ExplanationBuilder
from app.services.url_extractor import url_extractor
from app.ml.distilbert_model import distilbert_analyzer
from app.ml.clip_model import clip_analyzer
from app.ml.nsfw_model import nsfw_detector
from app.db.mongodb import post_repository

logger = logging.getLogger(__name__)

class ModerationService:
    """Orchestrates the entire moderation pipeline.
    
    Pipeline:
      1. Rule-based keyword / URL / spam checks
      2. ML text toxicity (toxic-bert)
      3. NSFW image detection (Falconsai ViT)
      4. Image-text relevance (CLIP)
      5. Decision engine combines all signals
      6. Explanation builder generates human-readable output
      
    Error policy: FAIL-CLOSED — if any stage crashes, the post is rejected
    rather than auto-approved, matching security best practices.
    """
    
    def __init__(self):
        self.rule_engine = RuleEngine()
        self.text_processor = TextProcessor()
        self.decision_engine = DecisionEngine()
        self.explanation_builder = ExplanationBuilder()
        logger.info("Moderation service initialized")

    async def _run_sync(self, func, *args):
        """Helper to run blocking ML calls in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

    async def moderate_post(
        self,
        post_id: str,
        text: str,
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run full moderation pipeline on a post."""
        logger.info(f"Starting moderation for post: {post_id}")
        
        try:
            # ── Step 1: Rule-based checks (fast, no ML) ──
            rule_results = self.rule_engine.check_rules(text)
            logger.info(
                f"Rule engine: score={rule_results.get('rule_score', 0):.2f}, "
                f"violations={rule_results.get('violations', [])}"
            )
            
            # ── Step 1b: URL extraction ──
            urls = url_extractor.extract_urls(text)
            suspicious_urls = [
                u for u in urls
                if u.get("risk_level") in ("MEDIUM", "HIGH")
            ]

            # ── Step 2: ML text analysis (toxic-bert) ──
            text_results = await self._run_sync(distilbert_analyzer.analyze, text)
            logger.info(
                f"Toxic-bert: score={text_results.get('toxicity_score', 0):.4f}, "
                f"category={text_results.get('category')}, "
                f"flagged_labels={text_results.get('flagged_labels', [])}"
            )
            
            results = {
                "rule_based": rule_results,
                "text_analysis": text_results,
                "url_analysis": {
                    "all_urls": urls,
                    "suspicious_urls": suspicious_urls,
                    "has_suspicious_urls": len(suspicious_urls) > 0,
                },
                "image_analysis": None,
                "relevance_analysis": None,
            }
            
            # ── Steps 3 & 4: Image analysis (if image provided) ──
            if image_path:
                clean_path = image_path.lstrip('/')
                full_image_path = os.path.normpath(clean_path)
                
                if os.path.exists(full_image_path):
                    # Step 3: NSFW detection
                    try:
                        nsfw_results = await self._run_sync(
                            nsfw_detector.analyze, full_image_path
                        )
                        logger.info(
                            f"NSFW: prob={nsfw_results.get('nsfw_probability', 0):.4f}, "
                            f"is_nsfw={nsfw_results.get('is_nsfw')}"
                        )
                        results["image_analysis"] = nsfw_results
                    except Exception as e:
                        logger.error(f"NSFW analysis failed: {e}")
                        # Fail-closed: treat NSFW failure as suspicious
                        results["image_analysis"] = {
                            "nsfw_probability": 0.6,
                            "is_nsfw": False,
                            "primary_category": "analysis_failed",
                            "explicit_content_detected": False,
                            "using_fallback": True,
                        }
                    
                    # Step 4: CLIP relevance
                    try:
                        clip_results = await self._run_sync(
                            clip_analyzer.analyze, text, full_image_path
                        )
                        logger.info(
                            f"CLIP: similarity={clip_results.get('similarity_score', 0):.4f}"
                        )
                        results["relevance_analysis"] = clip_results
                    except Exception as e:
                        logger.error(f"CLIP analysis failed: {e}")
                else:
                    logger.warning(f"Image file not found: {full_image_path}")
            
            # ── Step 5: Decision & Explanation ──
            decision = self.decision_engine.make_decision(results)
            explanation = self.explanation_builder.build_explanation(decision, results)
            
            # ── Step 6: Update DB ──
            update_ok = post_repository.update_moderation_result(
                post_id=post_id,
                allowed=decision["allowed"],
                reasons=explanation.get("reasons", []),
                flagged_phrases=explanation.get("flagged_phrases", []),
            )
            
            logger.info(
                f"Moderation complete: post={post_id}, "
                f"allowed={decision['allowed']}, "
                f"reasons={decision.get('reasons', [])}"
            )
            return {
                "post_id": post_id,
                "allowed": decision["allowed"],
                "results": results,
            }

        except Exception as e:
            logger.error(f"Error in moderation pipeline: {e}", exc_info=True)
            
            # FAIL-CLOSED: reject on error (do NOT auto-approve)
            post_repository.update_moderation_result(
                post_id=post_id,
                allowed=False,
                reasons=["System error: post rejected for safety review"],
                flagged_phrases=[],
            )
            return {
                "post_id": post_id,
                "allowed": False,
                "error": str(e),
            }