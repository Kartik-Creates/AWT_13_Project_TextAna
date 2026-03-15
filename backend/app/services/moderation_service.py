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
from app.ml.roberta_model import roberta_analyzer
from app.ml.clip_model import clip_analyzer
from app.ml.nsfw_model import nsfw_detector
from app.db.mongodb import post_repository

logger = logging.getLogger(__name__)

class ModerationService:
    """Orchestrates the entire moderation pipeline.
    
    Pipeline:
      1. Rule-based keyword / URL / spam checks
      2. ML text toxicity (XLM-RoBERTa)
      3. NSFW image detection (Falconsai/nsfw_image_detection)
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

    async def _record_metrics(self, post_id: str, text: str, results: Dict[str, Any]) -> None:
        """Best-effort background metrics recording (non-blocking for main pipeline)."""
        from app.services.metrics_repository import metrics_repository
        from datetime import datetime
        import time

        try:
            timestamp = datetime.utcnow()

            # Text model metrics
            text_res = results.get("text_analysis") or {}
            if text_res:
                hindi = text_res.get("hindi_detection") or {}
                lang = "hindi" if hindi.get("has_hindi_abuse") else "unknown"
                doc = {
                    "timestamp": timestamp,
                    "model": "roberta",
                    "input_type": "text",
                    "input_preview": text[:200],
                    "prediction": {
                        "category": text_res.get("category"),
                        "is_toxic": text_res.get("is_toxic"),
                        "toxicity_score": text_res.get("toxicity_score"),
                        "label_scores": text_res.get("label_scores", {}),
                    },
                    "confidence": float(text_res.get("confidence", 0.0)),
                    "response_time_ms": text_res.get("response_time_ms"),
                    "language": lang,
                    "category": text_res.get("category"),
                    "correct": None,
                    "user_feedback": None,
                    "post_id": post_id,
                }
                metrics_repository.insert_prediction(doc)

            # Image NSFW metrics
            image_res = results.get("image_analysis") or {}
            if image_res:
                doc = {
                    "timestamp": timestamp,
                    "model": "efficientnet",
                    "input_type": "image",
                    "input_preview": "[image]",
                    "prediction": {
                        "primary_category": image_res.get("primary_category"),
                        "is_nsfw": image_res.get("is_nsfw"),
                        "nsfw_probability": image_res.get("nsfw_probability"),
                    },
                    "confidence": float(
                        image_res.get(
                            "nsfw_probability",
                            0.0,
                        )
                    ),
                    "response_time_ms": image_res.get("response_time_ms"),
                    "language": None,
                    "category": "nsfw" if image_res.get("is_nsfw") else "safe",
                    "correct": None,
                    "user_feedback": None,
                    "post_id": post_id,
                }
                metrics_repository.insert_prediction(doc)

            # CLIP relevance metrics
            clip_res = results.get("relevance_analysis") or {}
            if clip_res:
                doc = {
                    "timestamp": timestamp,
                    "model": "clip",
                    "input_type": "pair",
                    "input_preview": text[:200],
                    "prediction": {
                        "similarity_score": clip_res.get("similarity_score"),
                        "is_relevant": clip_res.get("is_relevant"),
                        "mismatch_detected": clip_res.get("mismatch_detected"),
                    },
                    "confidence": float(
                        abs(clip_res.get("similarity_score", 0.0))
                    ),
                    "response_time_ms": clip_res.get("response_time_ms"),
                    "language": None,
                    "category": "mismatch"
                    if clip_res.get("mismatch_detected")
                    else "safe",
                    "correct": None,
                    "user_feedback": None,
                    "post_id": post_id,
                }
                metrics_repository.insert_prediction(doc)

        except Exception as e:
            logger.error(f"Failed to record metrics for post {post_id}: {e}", exc_info=True)

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

            # ── Step 2: ML text analysis (multilingual toxicity model: XLM-RoBERTa) ──
            text_results = await self._run_sync(roberta_analyzer.analyze, text)
            logger.info(
                f"Toxicity model: score={text_results.get('toxicity_score', 0):.4f}, "
                f"category={text_results.get('category')}, "
                f"flagged_labels={text_results.get('flagged_labels', [])}"
            )
            
            # Log Hindi detection if present
            hindi = text_results.get("hindi_detection") or {}
            if hindi.get("has_hindi_abuse"):
                logger.warning(
                    f"Hindi abuse detected: {hindi.get('matched_words', [])}"
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

            # ── Metrics recording (non-blocking) ──
            try:
                asyncio.create_task(
                    self._record_metrics(post_id=post_id, text=text, results=results)
                )
            except RuntimeError:
                # If no running loop, just fire-and-forget synchronously
                await self._record_metrics(post_id=post_id, text=text, results=results)
            
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