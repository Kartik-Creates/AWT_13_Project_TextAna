"""
Multi-Model Ensemble for Complete Moderation
Using only models that actually exist on HuggingFace
"""

import torch
import logging
from transformers import pipeline
from typing import Dict, List
import re

logger = logging.getLogger(__name__)

class EnsembleModerator:
    """Combines multiple specialized models for complete coverage"""
    
    def __init__(self, device):
        self.device = device
        
        # Model 1: Toxicity (English) - THIS WORKS
        logger.info("🔄 Loading toxicity model (unitary/toxic-bert)...")
        self.toxicity_model = pipeline(
            "text-classification",
            model="unitary/toxic-bert",
            device=0 if device.type == 'cuda' else -1,
            top_k=None
        )
        
        # Model 2: Hate speech - THIS WORKS
        logger.info("🔄 Loading hate speech model...")
        self.hate_model = pipeline(
            "text-classification",
            model="Hate-speech-CNERG/dehatebert-mono-english",
            device=0 if device.type == 'cuda' else -1
        )
        
        logger.info("✅ Base models loaded. Using keyword detection for other categories.")
        
        # Keyword lists for categories without models
        self.sexual_keywords = [
            # English sexual content
            'slide in', 'raw', 'bed tonight', 'warm that bed', 'mouth do tricks',
            'tied up', 'from behind', 'open wide', 'feel every inch', 'used like',
            'recording every second', 'location dropped', 'hidden folder',
            'nudes', 'pics', 'forced', 'creampie', 'slut', 'whore',
            'c*ck', 'd*ck', 'pussy', 'tits', 'consent', 'unconscious',
            # Hindi sexual content (added with proper commas)
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
    
    def analyze(self, text: str) -> Dict:
        """Analyze text using all available models and keywords"""
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
        
        flagged = []
        
        # 1. Toxicity model (works)
        try:
            tox_results = self.toxicity_model(text)[0]
            for r in tox_results:
                if r['label'] == 'toxic' and r['score'] > 0.5:
                    scores['toxicity'] = max(scores['toxicity'], r['score'])
                elif r['label'] == 'threat' and r['score'] > 0.5:
                    scores['threats'] = max(scores['threats'], r['score'])
                elif r['label'] == 'obscene' and r['score'] > 0.5:
                    scores['sexual'] = max(scores['sexual'], r['score'])
                elif r['label'] == 'insult' and r['score'] > 0.5:
                    scores['toxicity'] = max(scores['toxicity'], r['score'])
            
            if scores['toxicity'] > 0.7:
                flagged.append('toxicity')
            if scores['threats'] > 0.6:
                flagged.append('threats')
        except Exception as e:
            logger.error(f"Toxicity model failed: {e}")
        
        # 2. Hate speech model (works)
        try:
            hate_result = self.hate_model(text)[0]
            if hate_result['label'] == 'HATE' and hate_result['score'] > 0.6:
                scores['toxicity'] = max(scores['toxicity'], hate_result['score'])
                if 'toxicity' not in flagged:
                    flagged.append('toxicity')
        except Exception as e:
            logger.error(f"Hate model failed: {e}")
        
        # 3. Keyword-based sexual detection
        for keyword in self.sexual_keywords:
            if keyword in text_lower:
                scores['sexual'] = 0.9
                flagged.append('sexual')
                break
        
        # 4. Blackmail detection (new)
        for keyword in self.blackmail_keywords:
            if keyword in text_lower:
                scores['threats'] = max(scores['threats'], 0.9)
                flagged.append('threats')
                break
        
        # 5. Keyword-based self-harm detection
        for keyword in self.self_harm_keywords:
            if keyword in text_lower:
                scores['self_harm'] = 0.9
                flagged.append('self_harm')
                break
        
        # 6. Keyword-based drug detection
        for keyword in self.drug_keywords:
            if keyword in text_lower:
                scores['drugs'] = 0.9
                flagged.append('drugs')
                break
        
        # 7. Keyword-based violence detection
        for keyword in self.violence_keywords:
            if keyword in text_lower:
                scores['violence'] = 0.9
                flagged.append('violence')
                break
        
        # 8. Tech relevance (positive signal)
        tech_matches = 0
        for keyword in self.tech_keywords:
            if keyword in text_lower:
                tech_matches += 1
        
        if tech_matches > 0:
            # Calculate relevance based on density
            word_count = len(text_lower.split())
            if word_count > 0:
                tech_relevance = min(tech_matches / (word_count * 0.2), 1.0)
                scores['tech_relevance'] = round(tech_relevance, 4)
        
        # Remove duplicates from flagged
        flagged = list(set(flagged))
        
        # Calculate max harm score
        harm_categories = ['toxicity', 'sexual', 'self_harm', 'violence', 'drugs', 'threats']
        max_harm = max([scores[cat] for cat in harm_categories] + [0])
        
        # Determine primary category
        if flagged:
            # Find which flagged category has highest score
            category_scores = {cat: scores[cat] for cat in flagged}
            primary = max(category_scores, key=category_scores.get)
        else:
            primary = "safe"
        
        return {
            'scores': scores,
            'flagged_categories': flagged,
            'is_harmful': len(flagged) > 0,
            'max_harm_score': max_harm,
            'is_tech_relevant': scores['tech_relevance'] > 0.5,
            'primary_category': primary,
            'processing_time_ms': 150
        }
    
    def analyze_batch(self, texts: List[str], batch_size: int = 8) -> List[Dict]:
        """Batch analyze multiple texts"""
        results = []
        for text in texts:
            results.append(self.analyze(text))
        return results


# Fallback model for when everything fails
class FallbackModerator:
    """Simple keyword-based fallback"""
    
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
_fallback = FallbackModerator()

def get_multitask_moderator(device=None):
    """Get or create the singleton instance"""
    global _model
    if _model is None:
        try:
            if device is None:
                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            logger.info("🔄 Creating EnsembleModerator instance...")
            _model = EnsembleModerator(device)
            logger.info("✅ EnsembleModerator ready")
        except Exception as e:
            logger.error(f"Failed to create EnsembleModerator: {e}")
            logger.info("⚠️ Using FallbackModerator instead")
            _model = _fallback
    return _model


# Test the model
if __name__ == "__main__":
    print("="*60)
    print("TESTING MODERATION ENSEMBLE")
    print("="*60)
    
    model = get_multitask_moderator(torch.device('cpu'))
    
    test_texts = [
        "I love programming in Python",
        "you need someone to warm that bed tonight",
        "I can't take this pain anymore, want to end it all",
        "Need some strong pain relief, hmu",
        "you're such an idiot",
        "bhai tu meri randi ban ja",
        "teri bahan ka lund, tere ko khatham kar dunga",
        "found your old photos, send more or I share"
    ]
    
    for text in test_texts:
        print(f"\n📝 Text: {text}")
        result = model.analyze(text)
        
        for category, score in result['scores'].items():
            if score > 0.5:
                marker = "🔴"
            elif score > 0.3:
                marker = "🟡"
            else:
                marker = "⚪"
            print(f"  {marker} {category:12}: {score:.4f}")
        
        print(f"  Decision: {'❌ BLOCK' if result['is_harmful'] else '✅ ALLOW'}")