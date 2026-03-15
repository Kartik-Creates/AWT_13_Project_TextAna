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
from app.services.url_extractor import url_extractor # Re-added
from app.ml.distilbert_model import distilbert_analyzer
from app.ml.clip_model import clip_analyzer
from app.ml.nsfw_model import nsfw_detector
from app.db.mongodb import post_repository

logger = logging.getLogger(__name__)

class ModerationService:
    """Orchestrates the entire moderation pipeline (High Performance Version)"""
    
    def __init__(self):
        self.rule_engine = RuleEngine()
        self.text_processor = TextProcessor()
        self.decision_engine = DecisionEngine()
        self.explanation_builder = ExplanationBuilder()
        logger.info("Moderation service initialized")

    async def _run_sync(self, func, *args):
        """Helper to run blocking ML calls in a thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

    async def moderate_post(self, post_id: str, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Run full moderation pipeline on a post (Async/Non-blocking)
        """
        logger.info(f"Starting moderation for post: {post_id}")
        
        try:
            # Step 1: Rule-based (Fast)
            rule_results = self.rule_engine.check_rules(text)
            
            # Step 1b: URL Extraction (Re-added for safety)
            urls = url_extractor.extract_urls(text)
            suspicious_urls = [u for u in urls if u.get("risk_level") in ("MEDIUM", "HIGH")]

            # Step 2: Text analysis (Blocking ML -> Thread Pool)
            text_results = await self._run_sync(distilbert_analyzer.analyze, text)
            logger.info(f"DistilBERT Score: {text_results.get('toxicity_score', 0):.2f} Category: {text_results.get('category')}")
            
            results = {
                "rule_based": rule_results,
                "text_analysis": text_results,
                "url_analysis": {
                    "all_urls": urls,
                    "suspicious_urls": suspicious_urls,
                    "has_suspicious_urls": len(suspicious_urls) > 0
                },
                "image_analysis": None,
                "relevance_analysis": None
            }
            
            # Step 3 & 4: Image analysis
            if image_path:
                # Platform-safe path resolution
                clean_path = image_path.lstrip('/')
                full_image_path = os.path.normpath(clean_path)
                
                if os.path.exists(full_image_path):
                    # Step 3: NSFW (Blocking ML -> Thread Pool)
                    try:
                        nsfw_results = await self._run_sync(nsfw_detector.analyze, full_image_path)
                        logger.info(f"NSFW Probability: {nsfw_results.get('nsfw_probability', 0):.2f}")
                        results["image_analysis"] = nsfw_results
                    except Exception as e:
                        logger.error(f"NSFW analysis failed: {e}")
                    
                    # Step 4: CLIP (Blocking ML -> Thread Pool)
                    try:
                        clip_results = await self._run_sync(clip_analyzer.analyze, text, full_image_path)
                        logger.info(f"CLIP Relevance: {clip_results.get('similarity_score', 0):.2f}")
                        results["relevance_analysis"] = clip_results
                    except Exception as e:
                        logger.error(f"CLIP analysis failed: {e}")
                else:
                    logger.warning(f"Image file not found: {full_image_path}")
            
            # Step 5: Decision & Explanation
            decision = self.decision_engine.make_decision(results)
            explanation = self.explanation_builder.build_explanation(decision, results)
            
            # Step 6: Update DB
            update_ok = post_repository.update_moderation_result(
                post_id=post_id,
                allowed=decision["allowed"],
                reasons=explanation.get("reasons", []),
                flagged_phrases=explanation.get("flagged_phrases", [])
            )
            
            logger.info(f"Moderation complete for post: {post_id} - Allowed: {decision['allowed']}")
            return {"post_id": post_id, "allowed": decision["allowed"], "results": results}

        except Exception as e:
            logger.error(f"Error in moderation pipeline: {e}", exc_info=True)
            # Safe Fallback: Auto-approve on system error to avoid blocking users
            post_repository.update_moderation_result(
                 post_id=post_id, allowed=True, 
                 reasons=["System bypass: auto-approved on error"], 
                 flagged_phrases=[]
            )
            return {"post_id": post_id, "allowed": True, "error": str(e)}