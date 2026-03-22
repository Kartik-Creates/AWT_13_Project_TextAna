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
from app.ml.tech_context_filter import get_tech_context_filter
from app.ml.intent_entity_filter import get_intent_entity_filter
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
 
    class FallbackModerator:
        """Simple keyword-based fallback when ML model isn't available."""
 
        def __init__(self):
            logger.info("Initializing FallbackModerator with keyword rules")
 
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
 
        def analyze(self, text: str) -> Dict[str, Any]:
            """Analyze text using keyword matching."""
            text_lower = text.lower()
 
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
 
            for keyword in self.tech_keywords:
                if keyword in text_lower:
                    scores['tech_relevance'] = max(scores['tech_relevance'], 0.9)
 
            harmful_categories = ['drugs', 'sexual', 'self_harm', 'violence', 'threats']
            is_harmful = any(scores[cat] > 0.5 for cat in harmful_categories)
            max_harm = max([scores[cat] for cat in harmful_categories] + [0])
 
            return {
                'scores': scores,
                'flagged_categories': flagged_categories,
                'is_harmful': is_harmful,
                'max_harm_score': max_harm,
                'is_tech_relevant': scores['tech_relevance'] > 0.7,
                'primary_category': flagged_categories[0] if flagged_categories else 'safe',
                'processing_time_ms': 10
            }
 
    fallback_model = FallbackModerator()
 
 
class ModerationService:
    """Orchestrates the entire moderation pipeline.
 
    Pipeline:
      1. Rule-based harm checks (keywords / URLs / spam)
      2. Tech relevance scoring                          ← NEW
      3. Early exit for clear rule violations
      4. ML text toxicity analysis
      5. NSFW image detection
      6. Image-text relevance (CLIP)
      7. Decision engine (combines all signals)
      8. Explanation builder
      9. DB update + metrics
 
    Error policy: FAIL-CLOSED — crashes reject the post, not approve it.
    """
 
    def __init__(self):
        self.rule_engine = RuleEngine()
        self.text_processor = TextProcessor()
        self.decision_engine = DecisionEngine()
        self.explanation_builder = ExplanationBuilder()
        logger.info("✅ Moderation service initialized")
 
    async def _run_sync(self, func, *args):
        """Run blocking ML calls in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)
 
    async def _record_metrics(self, post_id: str, text: str, results: Dict[str, Any]) -> None:
        """Best-effort background metrics recording (non-blocking)."""
        from app.services.metrics_repository import metrics_repository
        from datetime import datetime
 
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
 
            # Tech relevance metrics
            tech_res = results.get("tech_relevance") or {}
            if tech_res:
                doc = {
                    "timestamp": timestamp,
                    "model": "rule_engine_tech",
                    "input_type": "text",
                    "input_preview": text[:200],
                    "prediction": {
                        "tech_relevance_score": tech_res.get("tech_relevance_score"),
                        "zone": tech_res.get("zone"),
                        "matched_categories": tech_res.get("matched_categories", []),
                        "matched_terms": tech_res.get("matched_terms", []),
                    },
                    "confidence": float(tech_res.get("tech_relevance_score", 0.0)),
                    "response_time_ms": None,
                    "language": "unknown",
                    "category": tech_res.get("zone", "unknown"),
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
                    "confidence": float(image_res.get("nsfw_probability", 0.0)),
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
                    "confidence": float(abs(clip_res.get("similarity_score", 0.0))),
                    "response_time_ms": clip_res.get("response_time_ms"),
                    "language": None,
                    "category": "mismatch" if clip_res.get("mismatch_detected") else "safe",
                    "correct": None,
                    "user_feedback": None,
                    "post_id": post_id,
                }
                metrics_repository.insert_prediction(doc)
 
            # TechContextFilter metrics
            tcf_res = results.get("tech_context_filter") or {}
            if tcf_res:
                doc = {
                    "timestamp": timestamp,
                    "model": "tech_context_filter",
                    "input_type": "text",
                    "input_preview": text[:200],
                    "prediction": {
                        "is_harmful": tcf_res.get("is_harmful", False),
                        "category": tcf_res.get("category"),
                        "confidence": tcf_res.get("confidence", 0.0),
                        "pattern_matched": tcf_res.get("pattern_matched", False),
                        "ml_used": tcf_res.get("ml_used", False),
                    },
                    "confidence": float(tcf_res.get("confidence", 0.0)),
                    "response_time_ms": tcf_res.get("processing_time_ms"),
                    "language": "unknown",
                    "category": tcf_res.get("category", "unknown"),
                    "correct": None,
                    "user_feedback": None,
                    "post_id": post_id,
                }
                metrics_repository.insert_prediction(doc)

            # IntentEntityFilter metrics
            ief_res = results.get("intent_entity_filter") or {}
            if ief_res:
                doc = {
                    "timestamp": timestamp,
                    "model": "intent_entity_filter",
                    "input_type": "text",
                    "input_preview": text[:200],
                    "prediction": {
                        "is_harmful": ief_res.get("is_harmful", False),
                        "category": ief_res.get("category"),
                        "confidence": ief_res.get("confidence", 0.0),
                        "entity_boost": ief_res.get("entity_boost", 0.0),
                        "ml_used": ief_res.get("ml_used", False),
                    },
                    "confidence": float(ief_res.get("confidence", 0.0)),
                    "response_time_ms": ief_res.get("processing_time_ms"),
                    "language": "unknown",
                    "category": ief_res.get("category", "unknown"),
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
        logger.info(f"▶️  Starting moderation — post: {post_id}")
 
        try:
            # ── Step 1: Rule-based harm checks (fast, no ML) ──
            rule_results = self.rule_engine.check_rules(text)
 
            logger.info(f"📋 Rule engine — score={rule_results.get('rule_score', 0):.2f}, "
                        f"violations={rule_results.get('violations', [])}")
 
            if rule_results.get('banned_keywords'):
                logger.warning(f"   Banned keywords: {rule_results.get('banned_keywords')}")
            if rule_results.get('hindi_detection', {}).get('has_hindi_abuse'):
                logger.warning(f"   Hindi abuse: {rule_results.get('hindi_detection', {}).get('matched_words')}")
 
            # ── Step 2: Tech relevance scoring ──
            tech_relevance = self.rule_engine.check_tech_relevance(text)
 
            logger.info(
                f"🔍 Tech relevance — score={tech_relevance['tech_relevance_score']:.3f}, "
                f"zone={tech_relevance['zone']}, "
                f"categories={tech_relevance['matched_categories']}"
            )
 
            # ── Step 2b: URL extraction ──
            urls = url_extractor.extract_urls(text)
            suspicious_urls = [
                u for u in urls
                if u.get("risk_level") in ("MEDIUM", "HIGH")
            ]
            if suspicious_urls:
                logger.warning(f"   Suspicious URLs: {suspicious_urls}")
 
            # ── Step 2c: Advanced cyber-harm & intent filters ──
            tech_ctx_result = {}
            intent_result   = {}
            try:
                tech_ctx_result = await self._run_sync(get_tech_context_filter().analyze, text)
                logger.info(
                    f"🛡️  TechContextFilter — harmful={tech_ctx_result.get('is_harmful')}, "
                    f"category={tech_ctx_result.get('category')}, "
                    f"confidence={tech_ctx_result.get('confidence', 0):.3f}"
                )
            except Exception as e:
                logger.error(f"TechContextFilter failed: {e}", exc_info=True)
 
            try:
                intent_result = await self._run_sync(get_intent_entity_filter().analyze, text)
                logger.info(
                    f"🔎 IntentEntityFilter — harmful={intent_result.get('is_harmful')}, "
                    f"category={intent_result.get('category')}, "
                    f"confidence={intent_result.get('confidence', 0):.3f}"
                )
            except Exception as e:
                logger.error(f"IntentEntityFilter failed: {e}", exc_info=True)
 
            # Derive composite cyber-harm signal for decision engine
            tcf_score = tech_ctx_result.get('confidence', 0.0) if tech_ctx_result.get('is_harmful') else 0.0
            ief_score = intent_result.get('confidence', 0.0)   if intent_result.get('is_harmful')   else 0.0
            cyber_harm_score = max(tcf_score, ief_score)
            cyber_harm_category = (
                tech_ctx_result.get('category', '') if tcf_score >= ief_score and tcf_score > 0
                else intent_result.get('category', '')
            )
            content_mixing_detected = tech_relevance.get('mixing', {}).get('mixing_detected', False)
 
            # ── Early Exit A: Severe harm rule violation (skip tech check) ──
            if rule_results.get('rule_score', 0) > 0.8:
                logger.warning(
                    f"🛑 EARLY BLOCK — rule engine: score={rule_results.get('rule_score', 0):.2f}"
                )
                results = {
                    "rule_based": rule_results,
                    "tech_relevance": tech_relevance,
                    "text_analysis": {"scores": {}, "flagged_categories": []},
                    "url_analysis": {
                        "all_urls": urls,
                        "suspicious_urls": suspicious_urls,
                        "has_suspicious_urls": len(suspicious_urls) > 0,
                    },
                    "tech_context_filter": tech_ctx_result,
                    "intent_entity_filter": intent_result,
                }
                decision_input = {
                    'rule_score': rule_results.get('rule_score', 1.0),
                    'has_suspicious_urls': len(suspicious_urls) > 0,
                    'tech_relevance_score': tech_relevance['tech_relevance_score'],
                    'tech_zone': tech_relevance['zone'],
                    'text_score': tech_relevance['tech_relevance_score'],
                    'toxicity_score': 0.0,
                    'sexual_score': 0.0,
                    'self_harm_score': 0.0,
                    'violence_score': 0.0,
                    'drugs_score': 0.0,
                    'threats_score': 0.0,
                    'is_harmful': True,
                    'nsfw_score': 0.0,
                    'cyber_harm_score': cyber_harm_score,
                    'cyber_harm_category': cyber_harm_category,
                    'content_mixing_detected': content_mixing_detected,
                    'clip_similarity': None,
                }
                decision = self.decision_engine.make_decision(decision_input)
                explanation = self.explanation_builder.build_explanation(decision, results)
                post_repository.update_moderation_result(
                    post_id=post_id,
                    allowed=decision["allowed"],
                    reasons=explanation.get("reasons", []),
                    flagged_phrases=explanation.get("flagged_phrases", []),
                )
                return {"post_id": post_id, "allowed": decision["allowed"], "results": results}
 
            # ── Early Exit B: Clearly off-topic (skip expensive ML) ──
            if tech_relevance['zone'] == "off_topic":
                logger.warning(
                    f"🛑 EARLY BLOCK — off-topic: score={tech_relevance['tech_relevance_score']:.3f}"
                )
                results = {
                    "rule_based": rule_results,
                    "tech_relevance": tech_relevance,
                    "text_analysis": {"scores": {}, "flagged_categories": []},
                    "url_analysis": {
                        "all_urls": urls,
                        "suspicious_urls": suspicious_urls,
                        "has_suspicious_urls": len(suspicious_urls) > 0,
                    },
                    "image_analysis": None,
                    "relevance_analysis": None,
                    "tech_context_filter": tech_ctx_result,
                    "intent_entity_filter": intent_result,
                }
                decision_input = {
                    'rule_score': rule_results.get('rule_score', 0.0),
                    'has_suspicious_urls': len(suspicious_urls) > 0,
                    'tech_relevance_score': tech_relevance['tech_relevance_score'],
                    'tech_zone': tech_relevance['zone'],
                    'text_score': tech_relevance['tech_relevance_score'],
                    'toxicity_score': 0.0,
                    'sexual_score': 0.0,
                    'self_harm_score': 0.0,
                    'violence_score': 0.0,
                    'drugs_score': 0.0,
                    'threats_score': 0.0,
                    'is_harmful': False,
                    'nsfw_score': 0.0,
                    'cyber_harm_score': cyber_harm_score,
                    'cyber_harm_category': cyber_harm_category,
                    'content_mixing_detected': content_mixing_detected,
                }
                decision = self.decision_engine.make_decision(decision_input)
                explanation = self.explanation_builder.build_explanation(decision, results)
                post_repository.update_moderation_result(
                    post_id=post_id,
                    allowed=decision["allowed"],
                    reasons=explanation.get("reasons", []),
                    flagged_phrases=explanation.get("flagged_phrases", []),
                )
                return {"post_id": post_id, "allowed": decision["allowed"], "results": results}
 
            # ── Step 3: ML text analysis (only runs for tech/review zone posts) ──
            try:
                if USE_ML_MODEL:
                    model = get_multitask_moderator()
                    text_results = await self._run_sync(model.analyze, text)
                    logger.info("✅ Multi-task model analysis complete")
                else:
                    text_results = fallback_model.analyze(text)
                    logger.info("✅ Fallback model analysis complete")
 
                logger.info(
                    f"📊 Text analysis — harmful={text_results.get('is_harmful', False)}, "
                    f"flagged={text_results.get('flagged_categories', [])}"
                )
 
            except Exception as e:
                logger.error(f"❌ Text analysis failed: {e}", exc_info=True)
                text_results = fallback_model.analyze(text)
                logger.info("⚠️  Used fallback after ML failure")
 
            results = {
                "rule_based": rule_results,
                "tech_relevance": tech_relevance,
                "text_analysis": text_results,
                "url_analysis": {
                    "all_urls": urls,
                    "suspicious_urls": suspicious_urls,
                    "has_suspicious_urls": len(suspicious_urls) > 0,
                },
                "image_analysis": None,
                "relevance_analysis": None,
                "tech_context_filter": tech_ctx_result,
                "intent_entity_filter": intent_result,
            }
 
            # ── Steps 4 & 5: Image analysis ──
            nsfw_score = 0.0
            if image_path:
                clean_path = image_path.lstrip('/')
                full_image_path = os.path.normpath(clean_path)
 
                if os.path.exists(full_image_path):
                    try:
                        nsfw_results = await self._run_sync(nsfw_detector.analyze, full_image_path)
                        logger.info(
                            f"🖼️  NSFW — prob={nsfw_results.get('nsfw_probability', 0):.4f}, "
                            f"is_nsfw={nsfw_results.get('is_nsfw')}"
                        )
                        results["image_analysis"] = nsfw_results
                        nsfw_score = nsfw_results.get('nsfw_probability', 0)
                    except Exception as e:
                        logger.error(f"NSFW analysis failed: {e}")
                        nsfw_score = 0.6
                        results["image_analysis"] = {
                            "nsfw_probability": 0.6,
                            "is_nsfw": False,
                            "primary_category": "analysis_failed",
                            "explicit_content_detected": False,
                            "using_fallback": True,
                        }
 
                    try:
                        clip_results = await self._run_sync(clip_analyzer.analyze, text, full_image_path)
                        logger.info(
                            f"🔄 CLIP — similarity={clip_results.get('similarity_score', 0):.4f}"
                        )
                        results["relevance_analysis"] = clip_results
                    except Exception as e:
                        logger.error(f"CLIP analysis failed: {e}")
                else:
                    logger.warning(f"⚠️  Image file not found: {full_image_path}")
 
            # ── Step 6: Build decision input ──
            text_scores = text_results.get('scores', {})
 
            score_mapping = {
                'tech_relevance': 'text_score',
                'toxicity': 'toxicity_score',
                'sexual': 'sexual_score',
                'self_harm': 'self_harm_score',
                'violence': 'violence_score',
                'drugs': 'drugs_score',
                'threats': 'threats_score'
            }
 
            decision_input = {
                'rule_score': rule_results.get('rule_score', 0.0),
                'has_suspicious_urls': len(suspicious_urls) > 0,
                'is_harmful': text_results.get('is_harmful', False),
                'nsfw_score': nsfw_score,
                # Tech relevance from rule engine (authoritative)
                'tech_relevance_score': tech_relevance['tech_relevance_score'],
                'tech_zone': tech_relevance['zone'],
                # Cyber-harm & content-mixing signals from advanced filters
                'cyber_harm_score': cyber_harm_score,
                'cyber_harm_category': cyber_harm_category,
                'content_mixing_detected': content_mixing_detected,

                # CLIP image-text similarity score
                'clip_similarity': (results.get("relevance_analysis") or {}).get("similarity_score", None),
            }
 
            for model_key, decision_key in score_mapping.items():
                decision_input[decision_key] = text_scores.get(model_key, 0.0)
 
            # Fallback: if categories flagged but scores are zero, apply floor scores
            flagged = text_results.get('flagged_categories', [])
            if flagged and all(
                decision_input.get(k, 0) == 0
                for k in ['self_harm_score', 'violence_score', 'drugs_score', 'sexual_score', 'threats_score']
            ):
                logger.warning("⚠️  Flagged categories but zero scores — applying fallback scores")
                category_score_map = {
                    'self_harm': 'self_harm_score',
                    'violence': 'violence_score',
                    'drugs': 'drugs_score',
                    'sexual': 'sexual_score',
                    'threats': 'threats_score',
                    'toxicity': 'toxicity_score',
                }
                for category in flagged:
                    key = category_score_map.get(category)
                    if key:
                        decision_input[key] = 0.8
 
            logger.info(
                f"📊 Decision input — "
                + ", ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
                            for k, v in decision_input.items())
            )
 
            # ── Step 7: Decision & Explanation ──
            decision = self.decision_engine.make_decision(decision_input)
            explanation = self.explanation_builder.build_explanation(decision, results)
 
            # ── Step 8: Metrics (non-blocking) ──
            try:
                asyncio.create_task(
                    self._record_metrics(post_id=post_id, text=text, results=results)
                )
            except RuntimeError:
                await self._record_metrics(post_id=post_id, text=text, results=results)
 
            # ── Step 9: Update DB ──
            post_repository.update_moderation_result(
                post_id=post_id,
                allowed=decision["allowed"],
                reasons=explanation.get("reasons", []),
                flagged_phrases=explanation.get("flagged_phrases", []),
            )
 
            logger.info(
                f"✅ Moderation complete — post={post_id}, "
                f"allowed={decision['allowed']}, reasons={decision.get('reasons', [])}"
            )
 
            return {
                "post_id": post_id,
                "allowed": decision["allowed"],
                "results": results,
            }
 
        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}", exc_info=True)
            try:
                post_repository.update_moderation_result(
                    post_id=post_id,
                    allowed=False,
                    reasons=["System error: post rejected for safety review"],
                    flagged_phrases=[],
                )
            except Exception:
                pass
            return {"post_id": post_id, "allowed": False, "error": str(e)}
 