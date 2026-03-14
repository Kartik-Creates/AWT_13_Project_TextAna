import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from app.services.url_extractor import url_extractor    
from app.services.rule_engine import RuleEngine
from app.services.text_processor import TextProcessor
from app.services.decision_engine import DecisionEngine
from app.services.explanation_builder import ExplanationBuilder
from app.ml.distilbert_model import distilbert_analyzer
from app.ml.clip_model import clip_analyzer
from app.ml.nsfw_model import nsfw_detector
from app.db.mongodb import post_repository

logger = logging.getLogger(__name__)

class ModerationService:
    """Orchestrates the entire moderation pipeline"""
    
    def __init__(self):
        self.rule_engine = RuleEngine()
        self.text_processor = TextProcessor()
        self.decision_engine = DecisionEngine()
        self.explanation_builder = ExplanationBuilder()
        
        logger.info("Moderation service initialized")
    
    async def moderate_post(self, post_id: str, text: str, image_path: Optional[str] = None):
        """
        Run full moderation pipeline on a post
        """
        logger.info(f"Starting moderation for post: {post_id}")
        
        try:
            # Step 1: Rule-based filtering
            logger.info("Step 1: Running rule-based filtering")
            rule_results = self.rule_engine.check_rules(text)

            # URL Extraction and Analysis
            logger.info("Step 1b: Extracting and analyzing URLs")
            urls = url_extractor.extract_urls(text)
            suspicious_urls = [url for url in urls if url["risk_level"] in ["MEDIUM", "HIGH"]]
            
            # Step 2: Text classification with DistilBERT
            logger.info("Step 2: Running DistilBERT text analysis")
            text_results = distilbert_analyzer.analyze(text)
            
            # Initialize results dictionary with URL analysis
            results = {
                "rule_based": rule_results,
                "text_analysis": text_results,
                "url_analysis": {
                    "all_urls": urls,
                    "suspicious_urls": suspicious_urls,
                    "has_suspicious_urls": len(suspicious_urls) > 0,
                    "total_urls": len(urls)
                },
                "image_analysis": None,
                "relevance_analysis": None
            }
            
            # Step 3 & 4: Image analysis (if image exists)
            if image_path:
                # Remove leading /uploads if present
                if image_path.startswith('/uploads/'):
                    full_image_path = image_path[1:]  # Remove leading slash
                else:
                    full_image_path = image_path
                
                # Step 3: NSFW image detection
                logger.info("Step 3: Running NSFW image detection")
                nsfw_results = nsfw_detector.analyze(full_image_path)
                results["image_analysis"] = nsfw_results
                
                # Step 4: Image-text relevance with CLIP
                logger.info("Step 4: Running CLIP relevance analysis")
                clip_results = clip_analyzer.analyze(text, full_image_path)
                results["relevance_analysis"] = clip_results
            
            # Step 5: Decision engine
            logger.info("Step 5: Running decision engine")
            decision = self.decision_engine.make_decision(results)
            
            # Build explanation
            explanation = self.explanation_builder.build_explanation(
                decision, 
                results
            )
            
            # Update database
            logger.info(f"Updating database with moderation results for post: {post_id}")
            post_repository.update_moderation_result(
                post_id=post_id,
                allowed=decision["allowed"],
                reasons=explanation["reasons"],
                flagged_phrases=explanation["flagged_phrases"]
            )
            
            # Log summary
            logger.info(f"Moderation complete for post: {post_id} - Allowed: {decision['allowed']}")
            if results["url_analysis"]["has_suspicious_urls"]:
                logger.warning(f"Post {post_id} contained {len(suspicious_urls)} suspicious URLs")
            
        except Exception as e:
            logger.error(f"Error in moderation pipeline for post {post_id}: {e}")
            
            # Update database with error state
            post_repository.update_moderation_result(
                post_id=post_id,
                allowed=False,
                reasons=["Error during moderation: " + str(e)],
                flagged_phrases=[]
            )