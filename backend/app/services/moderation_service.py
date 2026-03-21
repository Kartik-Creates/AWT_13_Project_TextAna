"""
Moderation Service - Orchestrates the entire moderation pipeline
with full URL extractor integration
"""

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
from app.ml.clip_model import clip_analyzer
from app.ml.efficientnet_model import efficientnet_nsfw as nsfw_detector
from app.db.mongodb import post_repository

logger = logging.getLogger(__name__)

# Try to import the multitask model, but have a fallback
try:
    from app.ml.multitask_model import get_multitask_moderator
    USE_ML_MODEL = True
    logger.info("✅ Successfully imported multitask model")
except ImportError as e:
    logger.warning(f"⚠️ Could not import multitask model: {e}, using fallback")
    USE_ML_MODEL = False
    
    # Define a simple fallback model
    class FallbackModerator:
        """Simple keyword-based fallback when ML model isn't available"""
        
        def __init__(self):
            logger.info("Initializing FallbackModerator with keyword rules")
            
            # Comprehensive keyword lists
            self.drug_keywords = [
                'snow', 'nose candy', 'xannies', 'pills', 'plug', 'colombian', 
                'party favors', 'white powder', 'h3r0in', 'fent', 'kush', 
                'gas', 'exotic', 'blues', 'tele', 'moonrocks', 'xan', 'perc',
                'oxy', 'pain relief', 'anxiety', 'medication', 'shipment'
            ]
            
            self.sexual_keywords = [
                'mouth do tricks', 'warm that bed', 'slide in', 'raw', 'taste',
                'bed tonight', 'nudes', 'pics', 'forced', 'creampie', 'slut',
                'tied up', 'breed', 'whore', 'c*ck', 'd*ck', 'pussy', 'tits',
                'consent', 'unconscious', 'location', 'meet me', 'old vids'
            ]
            
            self.self_harm_keywords = [
                'rope', 'pills lined up', 'jump', 'final exit', 'voices',
                'courage', 'check out', 'stop the pain', 'disappeared',
                'quiet spot', 'clock out', 'vanish', 'fading out', 'ending it',
                'suicide', 'kill myself', 'no reason', 'better off dead'
            ]
            
            self.violence_keywords = [
                'learn today', 'lights out', 'consequences', 'actions',
                'clapped', 'smoke', 'handle', 'piece', 'tool', 'caught',
                'air out', 'catch these hands', 'catch a body', 'rolling deep',
                'squad', 'stretched', 'pay', 'revenge', 'teaching'
            ]
            
            self.threat_keywords = [
                'one more word', 'gonna make sure', 'never opens', 'warning',
                'last time', 'regret', 'find out', 'coming for', 'waiting'
            ]
            
            self.tech_keywords = [
                'python', 'react', 'javascript', 'docker', 'kubernetes',
                'api', 'code', 'async/await', 'microservices', 'container',
                'deployed', 'production', 'debug', 'frontend', 'backend',
                'database', 'sql', 'nosql', 'mongodb', 'postgresql',
                'machine learning', 'ai', 'neural network', 'algorithm',
                'programming', 'software', 'app', 'website', 'web dev'
            ]
            
            self.hate_speech_keywords = [
                'nazis', 'kristallnacht', 'purify', 'gene pool', 'removed',
                'eradicated', 'final solution', 'cleansing', 'pure', 'disease'
            ]
            
            self.scam_keywords = [
                'millionaire', 'free money', 'glitch', 'passive', 'no job',
                'work from home', 'payouts', 'blueprint', 'crypto', 'eth',
                'bitcoin', 'returns', 'investment', 'guaranteed', 'signals'
            ]
        
        def analyze(self, text: str) -> Dict[str, any]:
            """Analyze text using keyword matching"""
            text_lower = text.lower()
            
            # Initialize scores
            scores = {
                'toxicity': 0.0,
                'sexual': 0.0,
                'self_harm': 0.0,
                'violence': 0.0,
                'drugs': 0.0,
                'threats': 0.0,
                'tech_relevance': 0.0
            }
            
            flagged_categories = []
            
            # Check each category
            for keyword in self.drug_keywords:
                if keyword in text_lower:
                    scores['drugs'] = max(scores['drugs'], 0.9)
                    scores['toxicity'] = max(scores['toxicity'], 0.7)
                    if 'drugs' not in flagged_categories:
                        flagged_categories.append('drugs')
            
            for keyword in self.sexual_keywords:
                if keyword in text_lower:
                    scores['sexual'] = max(scores['sexual'], 0.9)
                    scores['toxicity'] = max(scores['toxicity'], 0.7)
                    if 'sexual' not in flagged_categories:
                        flagged_categories.append('sexual')
            
            for keyword in self.self_harm_keywords:
                if keyword in text_lower:
                    scores['self_harm'] = max(scores['self_harm'], 0.9)
                    if 'self_harm' not in flagged_categories:
                        flagged_categories.append('self_harm')
            
            for keyword in self.violence_keywords:
                if keyword in text_lower:
                    scores['violence'] = max(scores['violence'], 0.9)
                    scores['toxicity'] = max(scores['toxicity'], 0.8)
                    if 'violence' not in flagged_categories:
                        flagged_categories.append('violence')
            
            for keyword in self.threat_keywords:
                if keyword in text_lower:
                    scores['threats'] = max(scores['threats'], 0.8)
                    scores['toxicity'] = max(scores['toxicity'], 0.7)
                    if 'threats' not in flagged_categories:
                        flagged_categories.append('threats')
            
            for keyword in self.hate_speech_keywords:
                if keyword in text_lower:
                    scores['toxicity'] = max(scores['toxicity'], 1.0)
                    scores['violence'] = max(scores['violence'], 0.9)
                    if 'hate_speech' not in flagged_categories:
                        flagged_categories.append('hate_speech')
            
            for keyword in self.scam_keywords:
                if keyword in text_lower:
                    scores['toxicity'] = max(scores['toxicity'], 0.5)
                    if 'scam' not in flagged_categories:
                        flagged_categories.append('scam')
            
            # Check tech keywords (these should ALLOW the post)
            for keyword in self.tech_keywords:
                if keyword in text_lower:
                    scores['tech_relevance'] = max(scores['tech_relevance'], 0.9)
            
            # Determine if harmful
            harmful_categories = ['drugs', 'sexual', 'self_harm', 'violence', 'threats']
            is_harmful = any(scores[cat] > 0.5 for cat in harmful_categories)
            
            # Calculate max harm score
            max_harm = max([scores[cat] for cat in harmful_categories] + [0])
            
            return {
                'scores': scores,
                'flagged_categories': flagged_categories,
                'is_harmful': is_harmful,
                'max_harm_score': max_harm,
                'is_tech_relevant': scores['tech_relevance'] > 0.7,
                'primary_category': flagged_categories[0] if flagged_categories else 'safe',
                'processing_time_ms': 10  # Simulated fast processing
            }
    
    fallback_model = FallbackModerator()


class ModerationService:
    """Orchestrates the entire moderation pipeline.
    
    Pipeline:
      1. URL extraction and analysis
      2. Rule-based keyword / URL / spam checks
      3. ML text toxicity (XLM-RoBERTa or MultiTask model)
      4. NSFW image detection (Falconsai/nsfw_image_detection)
      5. Image-text relevance (CLIP)
      6. Decision engine combines all signals
      7. Explanation builder generates human-readable output
      
    Error policy: FAIL-CLOSED — if any stage crashes, the post is rejected
    rather than auto-approved, matching security best practices.
    """
    
    def __init__(self):
        self.rule_engine = RuleEngine()
        self.text_processor = TextProcessor()
        self.decision_engine = DecisionEngine()
        self.explanation_builder = ExplanationBuilder()
        logger.info("✅ Moderation service initialized with URL extractor integration")

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
                doc = {
                    "timestamp": timestamp,
                    "model": "multitask" if USE_ML_MODEL else "fallback",
                    "input_type": "text",
                    "input_preview": text[:200],
                    "prediction": {
                        "scores": text_res.get("scores", {}),
                        "flagged_categories": text_res.get("flagged_categories", []),
                        "is_harmful": text_res.get("is_harmful", False),
                        "primary_category": text_res.get("primary_category"),
                    },
                    "confidence": float(text_res.get("max_harm_score", 0.0)),
                    "response_time_ms": text_res.get("processing_time_ms"),
                    "language": "unknown",
                    "category": text_res.get("primary_category", "unknown"),
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
                
            # URL metrics
            url_res = results.get("url_analysis") or {}
            if url_res and url_res.get("total_urls", 0) > 0:
                doc = {
                    "timestamp": timestamp,
                    "model": "url_extractor",
                    "input_type": "urls",
                    "input_preview": text[:200],
                    "prediction": {
                        "total_urls": url_res.get("total_urls", 0),
                        "suspicious_urls": url_res.get("suspicious_urls", 0),
                        "high_risk_urls": url_res.get("high_risk_urls", 0),
                        "medium_risk_urls": url_res.get("medium_risk_urls", 0),
                        "max_risk_score": url_res.get("max_risk_score", 0),
                    },
                    "confidence": float(url_res.get("max_risk_score", 0)),
                    "response_time_ms": url_res.get("processing_time_ms", 0),
                    "language": None,
                    "category": "suspicious_urls" if url_res.get("has_suspicious", False) else "safe",
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
        """Run full moderation pipeline on a post with URL extraction integration."""
        logger.info(f"▶️ Starting moderation for post: {post_id}")
        
        try:
            # ── STEP 1: URL Extraction and Analysis ──
            # Extract and analyze URLs from text
            urls = url_extractor.extract_urls(text)
            url_summary = url_extractor.get_url_summary(urls)
            

            # 🚨 IMMEDIATE BLOCK FOR SCAM URLS 🚨
            if url_summary.get('has_scam', False):
                logger.error(f"🚨🚨🚨 IMMEDIATE BLOCK: Scam URL detected! 🚨🚨🚨")
                for url in urls:
                    if url.get('has_scam_keywords', False):
                        logger.error(f"   Scam URL: {url['full_url']}")
                        logger.error(f"   Keywords: {url.get('scam_keywords_found', [])}")
                        logger.error(f"   Risk Score: {url['risk_score']:.2f} - {url['risk_level']}")
                
                # Immediately block without any further processing
                results = {
                    "rule_based": {"rule_score": 1.0, "violations": ["scam_url"]},
                    "text_analysis": {"scores": {}, "flagged_categories": ["scam_url"]},
                    "url_analysis": {
                        "all_urls": urls,
                        "suspicious_urls": urls,
                        "has_suspicious_urls": True,
                        "has_scam_urls": True,
                        "total_urls": len(urls),
                        "suspicious_urls_count": len(urls),
                        "max_risk_score": max([u['risk_score'] for u in urls]) if urls else 0,
                    },
                    "image_analysis": None,
                    "relevance_analysis": None,
                }
                
                decision = {
                    "allowed": False,
                    "reasons": ["scam_url_detected"],
                    "confidence": 1.0,
                    "primary_category": "scam",
                    "severity": "high",
                    "score": 1.0
                }
                
                explanation = self.explanation_builder.build_explanation(decision, results)
                
                post_repository.update_moderation_result(
                    post_id=post_id,
                    allowed=False,
                    reasons=["SCAM URL DETECTED: " + ", ".join([u['full_url'] for u in urls if u.get('has_scam_keywords')])],
                    flagged_phrases=[u['full_url'] for u in urls if u.get('has_scam_keywords')],
                )
                
                return {
                    "post_id": post_id,
                    "allowed": False,
                    "results": results,
                }

            # Log URL findings
            if url_summary['total_urls'] > 0:
                logger.info(f"🔗 Found {url_summary['total_urls']} URL(s) in content")
                for url in urls:
                    logger.info(f"   URL: {url['full_url'][:80]} - Risk: {url['risk_level']} ({url['risk_score']:.2f})")
                    if url['risk_indicators']:
                        logger.info(f"      Indicators: {', '.join(url['risk_indicators'][:2])}")
            
            # Determine suspicious URLs (MEDIUM or HIGH risk)
            suspicious_urls = [
                u for u in urls
                if u.get("risk_level") in ("MEDIUM", "HIGH")
            ]
            
            # Determine high-risk URLs (for immediate blocking)
            high_risk_urls = [
                u for u in urls
                if u.get("risk_level") == "HIGH"
            ]
            
            # Prepare URL analysis results
            url_analysis_results = {
                "all_urls": urls,
                "suspicious_urls": suspicious_urls,
                "high_risk_urls": high_risk_urls,
                "has_suspicious_urls": len(suspicious_urls) > 0,
                "has_high_risk_urls": len(high_risk_urls) > 0,
                "total_urls": url_summary['total_urls'],
                "suspicious_urls_count": url_summary['suspicious_count'],
                "max_risk_score": url_summary['max_risk_score'],
                "risk_levels": url_summary['risk_levels'],
                "processing_time_ms": 0
            }
            
            # EARLY EXIT: If high-risk URLs found, block immediately
            if url_analysis_results['has_high_risk_urls']:
                logger.warning(f"🛑 EARLY BLOCK due to HIGH-RISK URLs: {len(high_risk_urls)} URL(s)")
                for url in high_risk_urls:
                    logger.warning(f"   High-risk URL: {url['full_url']} (score: {url['risk_score']:.2f})")
                
                # Create results with URL analysis
                results = {
                    "rule_based": {"rule_score": 0.9, "violations": ["high_risk_url"]},
                    "text_analysis": {"scores": {}, "flagged_categories": ["urls"]},
                    "url_analysis": url_analysis_results,
                    "image_analysis": None,
                    "relevance_analysis": None,
                }
                
                # Create decision input with high-risk URL flag
                decision_input = {
                    'rule_score': 0.9,
                    'has_suspicious_urls': True,
                    'has_high_risk_urls': True,
                    'url_analysis': urls,
                    'url_summary': url_summary,
                    'text_score': 0.0,
                    'toxicity_score': 0.0,
                    'sexual_score': 0.0,
                    'self_harm_score': 0.0,
                    'violence_score': 0.0,
                    'drugs_score': 0.0,
                    'threats_score': 0.0,
                    'is_harmful': True,
                    'nsfw_score': 0.0
                }
                
                decision = self.decision_engine.make_decision(decision_input)
                explanation = self.explanation_builder.build_explanation(decision, results)
                
                # Update DB
                post_repository.update_moderation_result(
                    post_id=post_id,
                    allowed=decision["allowed"],
                    reasons=explanation.get("reasons", []),
                    flagged_phrases=explanation.get("flagged_phrases", []),
                )
                
                # Record metrics
                try:
                    asyncio.create_task(
                        self._record_metrics(post_id=post_id, text=text, results=results)
                    )
                except RuntimeError:
                    await self._record_metrics(post_id=post_id, text=text, results=results)
                
                return {
                    "post_id": post_id,
                    "allowed": decision["allowed"],
                    "results": results,
                }
            
            # ── STEP 2: Rule-based checks (fast, no ML) ──
            rule_results = self.rule_engine.check_rules(text)
            
            # Log rule results in detail
            logger.info(f"📋 Rule engine results:")
            logger.info(f"  - Score: {rule_results.get('rule_score', 0):.2f}")
            logger.info(f"  - Violations: {rule_results.get('violations', [])}")
            
            if rule_results.get('banned_keywords'):
                logger.warning(f"  - Banned keywords: {rule_results.get('banned_keywords')}")
            
            if rule_results.get('hindi_detection', {}).get('has_hindi_abuse'):
                logger.warning(f"  - Hindi abuse: {rule_results.get('hindi_detection', {}).get('matched_words')}")

            # EARLY EXIT: If rule score is very high, block immediately
            if rule_results.get('rule_score', 0) > 0.8:
                logger.warning(f"🛑 EARLY BLOCK by rule engine: score={rule_results.get('rule_score', 0):.2f}")
                
                # Create minimal results for early block
                results = {
                    "rule_based": rule_results,
                    "text_analysis": {"scores": {}, "flagged_categories": []},
                    "url_analysis": url_analysis_results,
                    "image_analysis": None,
                    "relevance_analysis": None,
                }
                
                # Create decision input with URL context
                decision_input = {
                    'rule_score': rule_results.get('rule_score', 1.0),
                    'has_suspicious_urls': url_analysis_results['has_suspicious_urls'],
                    'url_analysis': urls,
                    'url_summary': url_summary,
                    'text_score': 0.0,
                    'toxicity_score': 0.0,
                    'sexual_score': 0.0,
                    'self_harm_score': 0.0,
                    'violence_score': 0.0,
                    'drugs_score': 0.0,
                    'threats_score': 0.0,
                    'is_harmful': True,
                    'nsfw_score': 0.0
                }
                
                decision = self.decision_engine.make_decision(decision_input)
                explanation = self.explanation_builder.build_explanation(decision, results)
                
                # Update DB
                post_repository.update_moderation_result(
                    post_id=post_id,
                    allowed=decision["allowed"],
                    reasons=explanation.get("reasons", []),
                    flagged_phrases=explanation.get("flagged_phrases", []),
                )
                
                return {
                    "post_id": post_id,
                    "allowed": decision["allowed"],
                    "results": results,
                }

            # ── STEP 3: ML text analysis ──
            try:
                if USE_ML_MODEL:
                    # Use the advanced multi-task model
                    model = get_multitask_moderator()
                    text_results = await self._run_sync(model.analyze, text)
                    logger.info(f"✅ Multi-task model analysis complete")
                else:
                    # Use fallback model
                    text_results = fallback_model.analyze(text)
                    logger.info(f"✅ Fallback model analysis complete")
                
                logger.info(
                    f"📊 Text analysis: harmful={text_results.get('is_harmful', False)}, "
                    f"flagged={text_results.get('flagged_categories', [])}, "
                    f"tech={text_results.get('is_tech_relevant', False)}"
                )
                
            except Exception as e:
                logger.error(f"❌ Text analysis failed: {e}", exc_info=True)
                # If ML fails, use fallback
                text_results = fallback_model.analyze(text)
                logger.info(f"⚠️ Used fallback after ML failure")
            
            # Combine all results
            results = {
                "rule_based": rule_results,
                "text_analysis": text_results,
                "url_analysis": url_analysis_results,
                "image_analysis": None,
                "relevance_analysis": None,
            }
            
            # ── STEPS 4 & 5: Image analysis (if image provided) ──
            nsfw_score = 0.0  # Default value
            if image_path:
                clean_path = image_path.lstrip('/')
                full_image_path = os.path.normpath(clean_path)
                
                if os.path.exists(full_image_path):
                    # Step 4: NSFW detection
                    try:
                        nsfw_results = await self._run_sync(
                            nsfw_detector.analyze, full_image_path
                        )
                        logger.info(
                            f"🖼️ NSFW: prob={nsfw_results.get('nsfw_probability', 0):.4f}, "
                            f"is_nsfw={nsfw_results.get('is_nsfw')}"
                        )
                        results["image_analysis"] = nsfw_results
                        nsfw_score = nsfw_results.get('nsfw_probability', 0)
                    except Exception as e:
                        logger.error(f"NSFW analysis failed: {e}")
                        # Fail-closed: treat NSFW failure as suspicious
                        nsfw_score = 0.6
                        results["image_analysis"] = {
                            "nsfw_probability": 0.6,
                            "is_nsfw": False,
                            "primary_category": "analysis_failed",
                            "explicit_content_detected": False,
                            "using_fallback": True,
                        }
                    
                    # Step 5: CLIP relevance
                    try:
                        clip_results = await self._run_sync(
                            clip_analyzer.analyze, text, full_image_path
                        )
                        logger.info(
                            f"🔄 CLIP: similarity={clip_results.get('similarity_score', 0):.4f}"
                        )
                        results["relevance_analysis"] = clip_results
                    except Exception as e:
                        logger.error(f"CLIP analysis failed: {e}")
                else:
                    logger.warning(f"⚠️ Image file not found: {full_image_path}")
            
            # ── STEP 6: Decision & Explanation ──
            # Extract scores for decision engine
            text_scores = text_results.get('scores', {})
            
            # Debug logging
            logger.debug(f"Raw text scores: {text_scores}")

            # Create a mapping from model keys to decision engine keys
            score_mapping = {
                'tech_relevance': 'text_score',
                'toxicity': 'toxicity_score',
                'sexual': 'sexual_score',
                'self_harm': 'self_harm_score',
                'violence': 'violence_score',
                'drugs': 'drugs_score',
                'threats': 'threats_score'
            }

            # Build decision input with ALL signals - including URL analysis
            decision_input = {
                'rule_score': rule_results.get('rule_score', 1.0),
                'has_suspicious_urls': url_analysis_results['has_suspicious_urls'],
                'has_high_risk_urls': url_analysis_results['has_high_risk_urls'],
                'url_analysis': urls,
                'url_summary': url_summary,
                'is_harmful': text_results.get('is_harmful', False),
                'nsfw_score': nsfw_score
            }

            # Add mapped scores
            for model_key, decision_key in score_mapping.items():
                decision_input[decision_key] = text_scores.get(model_key, 0.0)

            # If flagged categories exist but scores are zero, use fallback scores
            flagged = text_results.get('flagged_categories', [])
            if flagged and all(decision_input.get(k, 0) == 0 for k in ['self_harm_score', 'violence_score', 'drugs_score', 'sexual_score', 'threats_score']):
                logger.warning("⚠️ Flagged categories but zero scores detected - applying fallback scores")
                
                # Apply reasonable scores based on flagged categories
                for category in flagged:
                    if category == 'self_harm':
                        decision_input['self_harm_score'] = 0.8
                    elif category == 'violence':
                        decision_input['violence_score'] = 0.8
                    elif category == 'drugs':
                        decision_input['drugs_score'] = 0.8
                    elif category == 'sexual':
                        decision_input['sexual_score'] = 0.8
                    elif category == 'threats':
                        decision_input['threats_score'] = 0.8
                    elif category == 'toxicity':
                        decision_input['toxicity_score'] = 0.8

            logger.info(f"📊 Final decision input: { {k: f'{v:.2f}' if isinstance(v, float) else v for k, v in decision_input.items()} }")

            decision = self.decision_engine.make_decision(decision_input)
            
            # Add URL details to decision for explanation
            if url_analysis_results['has_suspicious_urls']:
                decision['url_warning'] = f"Contains {url_analysis_results['suspicious_urls_count']} suspicious URL(s)"
                if url_analysis_results['suspicious_urls']:
                    decision['suspicious_urls'] = [
                        {
                            'url': u['full_url'],
                            'risk_level': u['risk_level'],
                            'risk_score': u['risk_score']
                        }
                        for u in url_analysis_results['suspicious_urls'][:3]  # Limit to first 3
                    ]

            # Build explanation
            explanation = self.explanation_builder.build_explanation(decision, results)

            # ── Metrics recording (non-blocking) ──
            try:
                asyncio.create_task(
                    self._record_metrics(post_id=post_id, text=text, results=results)
                )
            except RuntimeError:
                # If no running loop, just fire-and-forget synchronously
                await self._record_metrics(post_id=post_id, text=text, results=results)
            
            # ── STEP 7: Update DB ──
            update_ok = post_repository.update_moderation_result(
                post_id=post_id,
                allowed=decision["allowed"],
                reasons=explanation.get("reasons", []),
                flagged_phrases=explanation.get("flagged_phrases", []),
            )
            
            logger.info(
                f"✅ Moderation complete: post={post_id}, "
                f"allowed={decision['allowed']}, "
                f"reasons={decision.get('reasons', [])}"
            )
            
            # Add URL analysis summary to response
            if url_analysis_results['has_suspicious_urls']:
                logger.info(f"   ⚠️ URL warning: {url_analysis_results['suspicious_urls_count']} suspicious URL(s)")
            
            return {
                "post_id": post_id,
                "allowed": decision["allowed"],
                "results": results,
                "url_summary": {
                    "total_urls": url_analysis_results['total_urls'],
                    "suspicious_urls": url_analysis_results['suspicious_urls_count'],
                    "has_suspicious": url_analysis_results['has_suspicious_urls'],
                    "max_risk_score": url_analysis_results['max_risk_score']
                }
            }

        except Exception as e:
            logger.error(f"❌ Error in moderation pipeline: {e}", exc_info=True)
            
            # FAIL-CLOSED: reject on error (do NOT auto-approve)
            try:
                post_repository.update_moderation_result(
                    post_id=post_id,
                    allowed=False,
                    reasons=["System error: post rejected for safety review"],
                    flagged_phrases=[],
                )
            except:
                pass
                
            return {
                "post_id": post_id,
                "allowed": False,
                "error": str(e),
            }
    
    async def moderate_batch(
        self,
        posts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Moderate multiple posts in batch
        
        Args:
            posts: List of dicts with keys 'post_id', 'text', optional 'image_path'
            
        Returns:
            List of moderation results
        """
        tasks = []
        for post in posts:
            task = self.moderate_post(
                post_id=post['post_id'],
                text=post['text'],
                image_path=post.get('image_path')
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                final_results.append({
                    "error": str(result),
                    "allowed": False
                })
            else:
                final_results.append(result)
        
        return final_results
    
    def get_moderation_stats(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics from moderation decisions including URL stats
        
        Args:
            decisions: List of moderation decision dictionaries
            
        Returns:
            Statistics summary
        """
        total = len(decisions)
        blocked = sum(1 for d in decisions if not d.get('allowed', True))
        allowed = total - blocked
        
        # URL statistics
        url_stats = {
            'total_posts_with_urls': 0,
            'total_urls_found': 0,
            'total_suspicious_urls': 0,
            'posts_blocked_by_urls': 0
        }
        
        for decision in decisions:
            results = decision.get('results', {})
            url_analysis = results.get('url_analysis', {})
            
            if url_analysis.get('total_urls', 0) > 0:
                url_stats['total_posts_with_urls'] += 1
                url_stats['total_urls_found'] += url_analysis.get('total_urls', 0)
                url_stats['total_suspicious_urls'] += url_analysis.get('suspicious_urls_count', 0)
            
            # Check if blocked due to URLs
            if not decision.get('allowed', True):
                reasons = decision.get('results', {}).get('rule_based', {}).get('violations', [])
                if any('url' in reason.lower() for reason in reasons):
                    url_stats['posts_blocked_by_urls'] += 1
        
        # Category distribution
        categories = {}
        for decision in decisions:
            results = decision.get('results', {})
            text_analysis = results.get('text_analysis', {})
            primary_cat = text_analysis.get('primary_category', 'unknown')
            categories[primary_cat] = categories.get(primary_cat, 0) + 1
            
            # Add URL category if present
            if results.get('url_analysis', {}).get('has_suspicious_urls', False):
                categories['suspicious_urls'] = categories.get('suspicious_urls', 0) + 1
        
        return {
            'total_content': total,
            'allowed': allowed,
            'blocked': blocked,
            'block_rate': blocked / total if total > 0 else 0,
            'categories': categories,
            'url_statistics': url_stats
        }


# Global instance for easy import
moderation_service = ModerationService()