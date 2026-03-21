"""
Multi-Model Ensemble for Complete Moderation
Using models from model_loader
"""

import torch
import logging
from typing import Dict, List, Optional
import re

# Import your model loader
from app.ml.model_loader import model_loader

logger = logging.getLogger(__name__)

class EnsembleModerator:
    """Combines multiple specialized models for complete coverage"""
    
    def __init__(self, device=None):
        if device is None:
            self.device = model_loader.device
        else:
            self.device = device
        
        logger.info(f"EnsembleModerator initializing on device: {self.device}")
        
        # Load toxicity model from model_loader
        try:
            logger.info("🔄 Loading toxicity model from model_loader...")
            self.toxicity_model, self.toxicity_tokenizer = model_loader.load_roberta()
            logger.info("✅ Toxicity model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load toxicity model: {e}")
            self.toxicity_model = None
            self.toxicity_tokenizer = None
        
        # Load hate speech model
        try:
            logger.info("🔄 Loading hate speech model...")
            from transformers import pipeline
            self.hate_model = pipeline(
                "text-classification",
                model="Hate-speech-CNERG/dehatebert-mono-english",
                device=0 if self.device.type == 'cuda' else -1
            )
            logger.info("✅ Hate speech model loaded")
        except Exception as e:
            logger.error(f"Failed to load hate speech model: {e}")
            self.hate_model = None
        
        # Keyword lists for categories without models
        self._init_keyword_lists()
        
        logger.info("✅ EnsembleModerator ready")
    
    def _init_keyword_lists(self):
        """Initialize keyword lists for detection"""
        
        self.sexual_keywords = [
            # English sexual content
            'slide in', 'raw', 'bed tonight', 'warm that bed', 'mouth do tricks',
            'tied up', 'from behind', 'open wide', 'feel every inch', 'used like',
            'recording every second', 'location dropped', 'hidden folder',
            'nudes', 'pics', 'forced', 'creampie', 'slut', 'whore',
            'c*ck', 'd*ck', 'pussy', 'tits', 'consent', 'unconscious',
            # Hindi sexual content
            'bahan ka lund', 'maa ka lund', 'behen ki chut', 'maa ki chut',
            'teri maa', 'teri behan', 'bahan ka', 'chut', 'lund', 'randi',
            'madarchod', 'behenchod', 'bhenchod', 'chutiya', 'gandu',
            'kutta', 'kutiya', 'harami', 'sala', 'saala', 'bhosdi', 'bhosdike'
        ]
        
        self.blackmail_keywords = [
            'found your photos', 'found your pics', 'send me more',
            'share these with everyone', 'your choice', 'don\'t make me',
            'you know what I want', 'old photos', 'old pics', 'hidden folder',
            'either you send', 'or I share', 'remember these?', 'remember this?',
            'leak these', 'post these', 'go public'
        ]
        
        self.self_harm_keywords = [
            'end it', 'kill myself', 'suicide', 'better off dead', 'no reason to live',
            'want to die', 'take my life', 'check out permanently', 'stop the pain',
            'disappear tonight', 'rope', 'jump', 'voices', 'courage', 'pills lined up',
            'final exit', 'quiet spot', 'clock out', 'vanish', 'fading out',
            'end it all', 'end my life', 'end everything'
        ]
        
        self.drug_keywords = [
            'white powder', 'nose candy', 'h3r0in', 'fent', 'kush', 'plug',
            'xannies', 'pills', 'pain relief', 'strong', 'hit fast', 'score',
            'colombian', 'snow', 'party favors', 'medication', 'shipment',
            'xan', 'perc', 'oxy', 'anxiety', 'meds', 'drugs', 'dope',
            'weed', 'coke', 'meth', 'crack', 'heroin', 'fentanyl'
        ]
        
        self.violence_keywords = [
            'kill you', 'beat you', 'hurt you', 'destroy you', 'make you pay',
            'get even', 'revenge', 'suffer', 'pain', 'blood', 'die',
            'clapped', 'smoke', 'handle', 'piece', 'tool', 'caught',
            'air out', 'catch these hands', 'catch a body', 'shoot', 'stab',
            'gun', 'knife', 'weapon', 'attack', 'hit', 'punch', 'kick'
        ]
        
        self.threat_keywords = [
            'coming for you', 'watch your back', 'last warning', 'find you',
            'know where you live', 'wait outside', 'final warning',
            'regret', 'pay for this', 'never forget', 'remember this',
            'gonna get you', 'going to get you', 'mark my words'
        ]
        
        self.tech_keywords = [
            'python', 'javascript', 'typescript', 'react', 'vue', 'angular',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp',
            'api', 'rest', 'graphql', 'database', 'sql', 'nosql',
            'algorithm', 'machine learning', 'ai', 'frontend', 'backend',
            'microservices', 'container', 'cloud', 'server', 'async', 'await',
            'debug', 'deploy', 'production', 'development', 'coding',
            'programming', 'software', 'app', 'website', 'postgresql',
            'mongodb', 'mysql', 'redis', 'elasticsearch', 'kafka',
            'fastapi', 'django', 'flask', 'spring', 'rails',
            'git', 'github', 'ci/cd', 'jenkins', 'terraform'
        ]
    
    def _analyze_toxicity(self, text: str) -> Dict[str, float]:
        """Analyze toxicity using the loaded model"""
        scores = {'toxicity': 0.0, 'sexual': 0.0, 'threats': 0.0}
        
        if self.toxicity_model is None:
            return scores
        
        try:
            from transformers import pipeline
            # Create pipeline from loaded model
            toxicity_pipeline = pipeline(
                "text-classification",
                model=self.toxicity_model,
                tokenizer=self.toxicity_tokenizer,
                device=0 if self.device.type == 'cuda' else -1,
                top_k=None
            )
            
            results = toxicity_pipeline(text)[0]
            
            for r in results:
                label = r['label'].lower()
                score = r['score']
                if label == 'toxic' and score > 0.5:
                    scores['toxicity'] = max(scores['toxicity'], score)
                elif label == 'threat' and score > 0.5:
                    scores['threats'] = max(scores['threats'], score)
                elif label == 'obscene' and score > 0.5:
                    scores['sexual'] = max(scores['sexual'], score)
                elif label == 'insult' and score > 0.5:
                    scores['toxicity'] = max(scores['toxicity'], score)
        except Exception as e:
            logger.error(f"Toxicity analysis failed: {e}")
        
        return scores
    
    def _analyze_hate(self, text: str) -> float:
        """Analyze hate speech"""
        if self.hate_model is None:
            return 0.0
        
        try:
            result = self.hate_model(text)[0]
            if result['label'] == 'HATE':
                return result['score']
        except Exception as e:
            logger.error(f"Hate analysis failed: {e}")
        
        return 0.0
    
    def _keyword_detection(self, text: str) -> Dict[str, float]:
        """Detect harmful content using keywords"""
        text_lower = text.lower()
        scores = {
            'sexual': 0.0,
            'self_harm': 0.0,
            'violence': 0.0,
            'drugs': 0.0,
            'threats': 0.0
        }
        
        # Sexual keywords
        for keyword in self.sexual_keywords:
            if keyword in text_lower:
                scores['sexual'] = 0.9
                break
        
        # Blackmail (threats)
        for keyword in self.blackmail_keywords:
            if keyword in text_lower:
                scores['threats'] = 0.9
                break
        
        # Self-harm
        for keyword in self.self_harm_keywords:
            if keyword in text_lower:
                scores['self_harm'] = 0.9
                break
        
        # Drugs
        for keyword in self.drug_keywords:
            if keyword in text_lower:
                scores['drugs'] = 0.9
                break
        
        # Violence
        for keyword in self.violence_keywords:
            if keyword in text_lower:
                scores['violence'] = 0.9
                break
        
        # Threats
        for keyword in self.threat_keywords:
            if keyword in text_lower:
                scores['threats'] = max(scores['threats'], 0.9)
                break
        
        return scores
    
    def _tech_relevance(self, text: str) -> float:
        """Calculate tech relevance score"""
        text_lower = text.lower()
        tech_matches = 0
        for keyword in self.tech_keywords:
            if keyword in text_lower:
                tech_matches += 1
        
        if tech_matches == 0:
            return 0.0
        
        word_count = len(text_lower.split())
        if word_count > 0:
            # More lenient tech relevance scoring
            relevance = min(tech_matches / max(word_count * 0.15, 1), 0.9)
            return relevance
        return 0.0
    
    def analyze(self, text: str) -> Dict:
        """Analyze text using all available models"""
        
        # Get scores from all sources
        tox_scores = self._analyze_toxicity(text)
        hate_score = self._analyze_hate(text)
        keyword_scores = self._keyword_detection(text)
        tech_score = self._tech_relevance(text)
        
        # Combine scores
        scores = {
            'toxicity': max(tox_scores['toxicity'], hate_score),
            'sexual': max(tox_scores['sexual'], keyword_scores['sexual']),
            'self_harm': keyword_scores['self_harm'],
            'violence': keyword_scores['violence'],
            'drugs': keyword_scores['drugs'],
            'threats': max(tox_scores['threats'], keyword_scores['threats']),
            'tech_relevance': tech_score
        }
        
        # Determine flagged categories
        flagged = []
        for category in ['sexual', 'self_harm', 'violence', 'drugs', 'threats']:
            if scores[category] > 0.5:
                flagged.append(category)
        
        if scores['toxicity'] > 0.7:
            flagged.append('toxicity')
        
        # Remove duplicates
        flagged = list(set(flagged))
        
        # Calculate max harm score
        harm_categories = ['toxicity', 'sexual', 'self_harm', 'violence', 'drugs', 'threats']
        max_harm = max([scores[cat] for cat in harm_categories] + [0])
        
        # Determine primary category
        if flagged:
            category_scores = {cat: scores.get(cat, 0) for cat in flagged}
            primary = max(category_scores, key=category_scores.get)
        else:
            primary = "safe"
        
        return {
            'scores': scores,
            'flagged_categories': flagged,
            'is_harmful': len(flagged) > 0,
            'max_harm_score': max_harm,
            'is_tech_relevant': tech_score > 0.5,
            'primary_category': primary,
            'processing_time_ms': 100  # Approximate
        }


class FallbackModerator:
    """Simple keyword-based fallback when models fail"""
    
    def __init__(self):
        logger.info("Initializing FallbackModerator")
        
        self.harmful_keywords = {
            'sexual': ['bed tonight', 'slide in', 'raw', 'nudes', 'pics', 'randi', 'madarchod', 'bhenchod'],
            'self_harm': ['kill myself', 'suicide', 'end it', 'rope', 'jump', 'end it all'],
            'drugs': ['h3r0in', 'fent', 'kush', 'plug', 'pills', 'drugs', 'dope'],
            'violence': ['kill you', 'beat you', 'clapped', 'smoke', 'shoot'],
            'threats': ['coming for you', 'watch your back', 'find you', 'gonna get you']
        }
        
        self.tech_keywords = ['python', 'react', 'docker', 'api', 'code', 'app', 'javascript', 'database']
    
    def analyze(self, text: str) -> Dict:
        text_lower = text.lower()
        scores = {cat: 0.0 for cat in ['toxicity', 'sexual', 'self_harm', 'violence', 'drugs', 'threats', 'tech_relevance']}
        flagged = []
        
        for category, keywords in self.harmful_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[category] = 0.9
                    flagged.append(category)
                    break
        
        for keyword in self.tech_keywords:
            if keyword in text_lower:
                scores['tech_relevance'] = 0.9
                break
        
        return {
            'scores': scores,
            'flagged_categories': list(set(flagged)),
            'is_harmful': len(flagged) > 0,
            'max_harm_score': 0.9 if flagged else 0.0,
            'is_tech_relevant': scores['tech_relevance'] > 0.5,
            'primary_category': flagged[0] if flagged else 'safe',
            'processing_time_ms': 5
        }


# Singleton
_model = None

def get_multitask_moderator(device=None):
    """Get or create the singleton instance"""
    global _model
    if _model is None:
        try:
            logger.info("🔄 Creating EnsembleModerator instance...")
            _model = EnsembleModerator(device)
            logger.info("✅ EnsembleModerator ready")
        except Exception as e:
            logger.error(f"Failed to create EnsembleModerator: {e}")
            logger.info("⚠️ Using FallbackModerator instead")
            _model = FallbackModerator()
    return _model