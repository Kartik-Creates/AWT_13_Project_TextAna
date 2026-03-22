"""
Multi-Model Ensemble for Complete Moderation.

Uses real HuggingFace models for toxicity + hate speech,
keyword detection for other harm categories, and integrates
with RuleEngine.check_tech_relevance() for accurate tech scoring.
"""

import torch
import logging
from transformers import pipeline
from typing import Dict, List, Optional, Any
import time

logger = logging.getLogger(__name__)


class EnsembleModerator:
    """Combines multiple specialized models for complete moderation coverage.

    Harm detection:
      - unitary/toxic-bert           → toxicity + threats + obscene
      - Hate-speech-CNERG/dehatebert → hate speech
      - Keyword lists                → sexual, self-harm, drugs, violence, threats

    IMPORTANT — keyword list design rules:
      - Every keyword must be specific enough that it CANNOT appear in a
        normal tech/business sentence without indicating real harm.
      - Generic words like "strong", "score", "hit", "pain", "medication",
        "anxiety", "pills" are BANNED from these lists — they cause false
        positives on tech content (e.g. "strong backend", "high score").
      - Multi-word phrases are always preferred over single words.

    Tech relevance:
      - Delegates to RuleEngine.check_tech_relevance() for authoritative scoring
      - Falls back to weighted keyword density if RuleEngine is unavailable
    """

    def __init__(self, device: torch.device):
        self.device = device

        # ── Model 1: Toxicity ──
        logger.info("🔄 Loading toxicity model (unitary/toxic-bert)...")
        self.toxicity_model = pipeline(
            "text-classification",
            model="unitary/toxic-bert",
            device=0 if device.type == 'cuda' else -1,
            top_k=None
        )

        # ── Model 2: Hate Speech ──
        logger.info("🔄 Loading hate speech model (dehatebert)...")
        self.hate_model = pipeline(
            "text-classification",
            model="Hate-speech-CNERG/dehatebert-mono-english",
            device=0 if device.type == 'cuda' else -1
        )

        logger.info("✅ Base ML models loaded.")

        # ── Harm keyword lists ──
        # RULE: Every entry must be specific. No single common words.
        # Multi-word phrases are preferred. If in doubt, leave it out.

        self.sexual_keywords = [
            # English — must be unambiguous sexual content
            'slide in my dms', 'warm that bed tonight', 'mouth do tricks',
            'tied up and', 'feel every inch', 'recording every second',
            'hidden folder of', 'send me nudes', 'send nudes',
            'sext me', 'sexting', 'sex tape', 'private video of you',
            'forced her to', 'breed you', 'creampie',
            'slut', 'whore', 'c*ck', 'd*ck',
            'rape', 'raped', 'raping', 'molest', 'molested',
            # Hindi / Hinglish — specific abusive phrases
            'bahan ka lund', 'maa ka lund', 'behen ki chut', 'maa ki chut',
            'meri randi ban', 'randi ban ja',
            'madarchod', 'behenchod', 'bhenchod', 'chutiya', 'gandu',
            'bhosdike', 'bhosdi',
        ]

        self.blackmail_keywords = [
            # Must be specific blackmail/extortion patterns
            'found your photos and', 'found your pics and',
            'send me more or i share', 'share these with everyone',
            "or i'll share", 'you know what i want or',
            'remember these photos', 'remember these pics',
            'i will leak', 'going to leak your', 'post your photos',
            'either you send or', 'your choice or i share',
        ]

        self.self_harm_keywords = [
            # Must be unambiguous self-harm intent — not casual phrases
            'kill myself', 'killing myself',
            'suicide note', 'end my life', 'take my own life',
            'hang myself', 'slit my wrists', 'overdose on purpose',
            'pills lined up to', 'want to jump off',
            'no reason to live', 'better off dead',
            'final exit plan', 'going to end it all',
            'disappear permanently', 'never wake up again',
            'ending it tonight', 'ending it all tonight',
        ]

        self.drug_keywords = [
            # Must be specific to illegal drug dealing/use context
            # REMOVED: 'strong', 'score', 'hit fast', 'pain relief', 'anxiety',
            #          'pills', 'medication', 'shipment', 'xan', 'perc', 'oxy'
            #          — all too generic and cause false positives on tech content
            'white powder for sale', 'nose candy', 'h3r0in', 'her0in',
            'fentanyl for sale', 'fent plug', 'plug for kush',
            'xannies for sale', 'bars for sale', 'pressed pills',
            'party favors for sale', 'dark web drugs',
            'colombian coke', 'selling coke', 'selling dope',
            'drug plug', 'drug dealer', 'selling weed', 'weed plug',
            'meth for sale', 'crystal for sale', 'crack for sale',
            'heroin plug', 'buy heroin', 'buy cocaine', 'buy meth',
            'mdma for sale', 'ecstasy for sale', 'lsd for sale',
        ]

        self.violence_keywords = [
            # Must be direct, specific threats — not general frustration
            # REMOVED: 'pain', 'blood', 'die', 'handle', 'piece', 'tool' — too generic
            'i will kill you', "i'm going to kill you", 'gonna kill you',
            'i will murder you', 'going to murder',
            'beat you to death', 'beat you up badly',
            'catch a body', 'catch these hands',
            'air you out', 'clap you', 'smoke you',
            'put a bullet in', 'shoot you up',
            'stab you', 'knife you',
            'bomb threat', 'blow up the',
            'mass shooting at', 'shoot up the',
        ]

        self.threat_keywords = [
            # Must be explicit personal threats — not general expressions
            # REMOVED: 'pain', 'revenge', 'regret', 'remember this' — too generic
            'coming for you tonight', 'i know where you live',
            'watch your back or', 'last warning or else',
            'wait outside your house', 'wait outside your school',
            'find you and', 'hunt you down',
            'gonna get you back for this',
            'make you pay for what you did',
            'you will regret crossing me',
            'next time i see you',
        ]

        # Fallback tech keywords used ONLY when RuleEngine is unavailable
        self._fallback_tech_keywords = [
            'python', 'javascript', 'typescript', 'react', 'vue', 'angular',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp',
            'api', 'rest', 'graphql', 'database', 'sql', 'nosql',
            'algorithm', 'machine learning', 'deep learning', 'ai',
            'frontend', 'backend', 'microservices', 'container',
            'cloud', 'server', 'async', 'await', 'debug', 'deploy',
            'production', 'coding', 'programming', 'software',
            'postgresql', 'mongodb', 'mysql', 'redis', 'elasticsearch',
            'kafka', 'fastapi', 'django', 'flask', 'spring', 'rails',
            'git', 'github', 'ci/cd', 'jenkins', 'terraform',
            'rust', 'golang', 'kotlin', 'swift', 'linux',
            'devops', 'helm', 'prometheus', 'grafana',
            'neural network', 'transformer', 'llm', 'pytorch', 'tensorflow',
            'application', 'architecture', 'scalable', 'performance',
            'developer', 'engineer', 'technology', 'digital', 'platform',
            'security', 'encryption', 'authentication', 'user experience',
        ]

        # Lazy-load RuleEngine for authoritative tech scoring
        self._rule_engine = self._load_rule_engine()

    def _load_rule_engine(self):
        """Try to import and return a RuleEngine instance for tech scoring."""
        try:
            from app.services.rule_engine import RuleEngine
            engine = RuleEngine()
            logger.info("✅ RuleEngine loaded into EnsembleModerator for tech scoring")
            return engine
        except Exception as e:
            logger.warning(
                f"⚠️  Could not load RuleEngine ({e}). "
                "Using fallback keyword-based tech scoring."
            )
            return None

    # ──────────────────────────────────────────────────────────
    #  Tech Relevance Scoring
    # ──────────────────────────────────────────────────────────

    def _score_tech_relevance(self, text: str) -> Dict[str, Any]:
        """Return tech relevance score and zone."""
        if self._rule_engine is not None:
            try:
                result = self._rule_engine.check_tech_relevance(text)
                return {
                    "score": result["tech_relevance_score"],
                    "zone": result["zone"],
                    "matched_categories": result.get("matched_categories", []),
                    "matched_terms": result.get("matched_terms", []),
                    "source": "rule_engine",
                }
            except Exception as e:
                logger.warning(f"RuleEngine tech scoring failed ({e}), using fallback")

        # Fallback: weighted keyword density
        text_lower = text.lower()
        word_count = max(len(text_lower.split()), 1)
        matches = sum(1 for kw in self._fallback_tech_keywords if kw in text_lower)

        if matches == 0:
            score = 0.0
        else:
            raw_density = matches / (word_count * 0.15)
            score = round(min(raw_density, 1.0), 4)

        zone = "tech" if score >= 0.38 else ("review" if score >= 0.20 else "off_topic")

        return {
            "score": score,
            "zone": zone,
            "matched_categories": [],
            "matched_terms": [],
            "source": "fallback_keywords",
        }

    # ──────────────────────────────────────────────────────────
    #  Keyword matching — phrase-aware
    # ──────────────────────────────────────────────────────────

    def _matches_any(self, text_lower: str, keywords: List[str]) -> bool:
        """Return True if any keyword is found in the text.

        Single-word keywords use word-boundary matching to avoid
        matching substrings. Multi-word keywords use substring match.
        """
        for keyword in keywords:
            if ' ' in keyword:
                # Multi-word phrase: substring match
                if keyword in text_lower:
                    return True
            else:
                # Single word: require word boundary
                import re
                if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                    return True
        return False

    # ──────────────────────────────────────────────────────────
    #  Main Analysis
    # ──────────────────────────────────────────────────────────

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text for harm categories and tech relevance."""
        start_ms = time.time()
        text_lower = text.lower()

        scores: Dict[str, float] = {
            'toxicity': 0.0,
            'sexual': 0.0,
            'self_harm': 0.0,
            'violence': 0.0,
            'drugs': 0.0,
            'threats': 0.0,
            'tech_relevance': 0.0,
        }

        flagged: List[str] = []

        # ── 1. Toxicity model ──
        try:
            tox_results = self.toxicity_model(text[:512])[0]
            for r in tox_results:
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

            if scores['toxicity'] > 0.7 and 'toxicity' not in flagged:
                flagged.append('toxicity')
            if scores['threats'] > 0.6 and 'threats' not in flagged:
                flagged.append('threats')
        except Exception as e:
            logger.error(f"Toxicity model failed: {e}")

        # ── 2. Hate speech model ──
        try:
            hate_result = self.hate_model(text[:512])[0]
            if hate_result['label'] == 'HATE' and hate_result['score'] > 0.6:
                scores['toxicity'] = max(scores['toxicity'], hate_result['score'])
                if 'toxicity' not in flagged:
                    flagged.append('toxicity')
        except Exception as e:
            logger.error(f"Hate speech model failed: {e}")

        # ── 3. Sexual content ──
        if self._matches_any(text_lower, self.sexual_keywords):
            scores['sexual'] = max(scores['sexual'], 0.9)
            if 'sexual' not in flagged:
                flagged.append('sexual')

        # ── 4. Blackmail ──
        if self._matches_any(text_lower, self.blackmail_keywords):
            scores['threats'] = max(scores['threats'], 0.9)
            if 'threats' not in flagged:
                flagged.append('threats')

        # ── 5. Self-harm ──
        if self._matches_any(text_lower, self.self_harm_keywords):
            scores['self_harm'] = max(scores['self_harm'], 0.9)
            if 'self_harm' not in flagged:
                flagged.append('self_harm')

        # ── 6. Drugs ──
        if self._matches_any(text_lower, self.drug_keywords):
            scores['drugs'] = max(scores['drugs'], 0.9)
            if 'drugs' not in flagged:
                flagged.append('drugs')

        # ── 7. Violence ──
        if self._matches_any(text_lower, self.violence_keywords):
            scores['violence'] = max(scores['violence'], 0.9)
            if 'violence' not in flagged:
                flagged.append('violence')

        # ── 8. Threats ──
        if self._matches_any(text_lower, self.threat_keywords):
            scores['threats'] = max(scores['threats'], 0.85)
            if 'threats' not in flagged:
                flagged.append('threats')

        # ── 9. Tech relevance ──
        tech = self._score_tech_relevance(text)
        scores['tech_relevance'] = tech['score']

        # ── Aggregate ──
        flagged = list(set(flagged))
        harm_categories = ['toxicity', 'sexual', 'self_harm', 'violence', 'drugs', 'threats']
        max_harm = max((scores[cat] for cat in harm_categories), default=0.0)
        primary = max(flagged, key=lambda c: scores.get(c, 0)) if flagged else "safe"

        elapsed_ms = round((time.time() - start_ms) * 1000)

        return {
            'scores': scores,
            'flagged_categories': flagged,
            'is_harmful': len(flagged) > 0,
            'max_harm_score': max_harm,
            'is_tech_relevant': tech['zone'] == 'tech',
            'tech_relevance_score': tech['score'],
            'tech_zone': tech['zone'],
            'tech_matched_categories': tech.get('matched_categories', []),
            'primary_category': primary,
            'processing_time_ms': elapsed_ms,
        }

    def analyze_batch(self, texts: List[str], batch_size: int = 8) -> List[Dict[str, Any]]:
        """Batch analyze multiple texts."""
        return [self.analyze(text) for text in texts]


# ──────────────────────────────────────────────────────────────────────────────
#  Fallback: no ML models available
# ──────────────────────────────────────────────────────────────────────────────

class FallbackModerator:
    """Keyword-only fallback when ML models cannot be loaded."""

    def __init__(self):
        logger.info("Initializing FallbackModerator (keyword-only)")

        # Same strict keyword philosophy — specific phrases only, no generic words
        self.harmful_keywords: Dict[str, List[str]] = {
            'sexual': [
                'send nudes', 'sext me', 'sex tape',
                'rape', 'raped', 'molest', 'molested',
                'creampie', 'slut', 'whore',
                'meri randi ban', 'madarchod', 'behenchod', 'bhenchod',
                'chutiya', 'bhosdike',
            ],
            'self_harm': [
                'kill myself', 'end my life', 'hang myself',
                'suicide note', 'slit my wrists',
                'no reason to live', 'better off dead',
                'going to end it all', 'ending it tonight',
            ],
            'drugs': [
                'drug plug', 'drug dealer', 'selling weed', 'weed plug',
                'fentanyl for sale', 'fent plug',
                'heroin plug', 'buy heroin', 'buy cocaine', 'buy meth',
                'white powder for sale', 'nose candy', 'h3r0in',
                'mdma for sale', 'ecstasy for sale', 'lsd for sale',
                'pressed pills', 'dark web drugs',
            ],
            'violence': [
                'i will kill you', 'gonna kill you', 'going to murder',
                'beat you to death', 'catch a body',
                'air you out', 'shoot you up', 'stab you',
                'bomb threat', 'shoot up the', 'mass shooting',
            ],
            'threats': [
                'coming for you tonight', 'i know where you live',
                'last warning or else', 'wait outside your house',
                'hunt you down', 'find you and hurt',
                'make you pay for what you did',
            ],
        }

        self._fallback_tech_keywords = [
            'python', 'react', 'docker', 'kubernetes', 'api', 'code',
            'javascript', 'database', 'sql', 'backend', 'frontend',
            'machine learning', 'ai', 'deploy', 'server', 'github',
            'typescript', 'flask', 'fastapi', 'django', 'rust', 'golang',
            'application', 'architecture', 'scalable', 'performance',
            'developer', 'engineer', 'technology', 'digital', 'platform',
            'security', 'encryption', 'authentication', 'user experience',
        ]

        self._rule_engine = self._load_rule_engine()

    def _load_rule_engine(self):
        try:
            from app.services.rule_engine import RuleEngine
            engine = RuleEngine()
            logger.info("✅ RuleEngine loaded into FallbackModerator")
            return engine
        except Exception as e:
            logger.warning(f"⚠️  Could not load RuleEngine in FallbackModerator: {e}")
            return None

    def _score_tech_relevance(self, text: str) -> Dict[str, Any]:
        if self._rule_engine is not None:
            try:
                result = self._rule_engine.check_tech_relevance(text)
                return {
                    "score": result["tech_relevance_score"],
                    "zone": result["zone"],
                    "matched_categories": result.get("matched_categories", []),
                }
            except Exception as e:
                logger.warning(f"RuleEngine tech scoring failed in fallback: {e}")

        text_lower = text.lower()
        matches = sum(1 for kw in self._fallback_tech_keywords if kw in text_lower)
        score = round(min(matches / max(len(text_lower.split()) * 0.15, 1), 1.0), 4)
        zone = "tech" if score >= 0.38 else ("review" if score >= 0.20 else "off_topic")
        return {"score": score, "zone": zone, "matched_categories": []}

    def _matches_any(self, text_lower: str, keywords: List[str]) -> bool:
        """Phrase-aware keyword matching."""
        import re
        for keyword in keywords:
            if ' ' in keyword:
                if keyword in text_lower:
                    return True
            else:
                if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                    return True
        return False

    def analyze(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        scores = {cat: 0.0 for cat in [
            'toxicity', 'sexual', 'self_harm', 'violence', 'drugs', 'threats', 'tech_relevance'
        ]}
        flagged: List[str] = []

        for category, keywords in self.harmful_keywords.items():
            if self._matches_any(text_lower, keywords):
                scores[category] = 0.9
                flagged.append(category)

        tech = self._score_tech_relevance(text)
        scores['tech_relevance'] = tech['score']
        flagged = list(set(flagged))

        harm_categories = ['toxicity', 'sexual', 'self_harm', 'violence', 'drugs', 'threats']
        max_harm = max((scores[c] for c in harm_categories), default=0.0)

        return {
            'scores': scores,
            'flagged_categories': flagged,
            'is_harmful': len(flagged) > 0,
            'max_harm_score': max_harm,
            'is_tech_relevant': tech['zone'] == 'tech',
            'tech_relevance_score': tech['score'],
            'tech_zone': tech['zone'],
            'tech_matched_categories': tech.get('matched_categories', []),
            'primary_category': flagged[0] if flagged else 'safe',
            'processing_time_ms': 5,
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Singleton
# ──────────────────────────────────────────────────────────────────────────────

_model: Optional[Any] = None
_fallback = FallbackModerator()


def get_multitask_moderator(device: Optional[torch.device] = None) -> Any:
    """Return the global moderator instance, creating it on first call."""
    global _model
    if _model is None:
        try:
            if device is None:
                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            logger.info("🔄 Creating EnsembleModerator...")
            _model = EnsembleModerator(device)
            logger.info("✅ EnsembleModerator ready")
        except Exception as e:
            logger.error(f"Failed to create EnsembleModerator: {e}")
            logger.info("⚠️  Falling back to FallbackModerator")
            _model = _fallback
    return _model


# ──────────────────────────────────────────────────────────────────────────────
#  Quick test
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING MODERATION ENSEMBLE")
    print("=" * 60)

    model = get_multitask_moderator(torch.device('cpu'))

    test_texts = [
        # Should ALLOW
        "User experience defines the success of any application. Fast loading, smooth interactions, and intuitive design keep users engaged. Combining frontend performance with strong backend systems creates powerful and reliable digital products.",
        "Just deployed my FastAPI app on Kubernetes using Helm charts!",
        "Security in tech applications is critical. Protecting user data through encryption, authentication, and secure APIs ensures trust.",
        "Real-time communication using WebSockets and event-driven systems makes instant messaging possible.",
        "Python + React + Docker — my go-to stack for every new project.",
        # Should BLOCK
        "I will kill you tonight",
        "buy cocaine from my drug plug",
        "send nudes or i'll share your photos",
        "i want to kill myself, no reason to live",
        "I love watching cricket with my family every evening.",
    ]

    for text in test_texts:
        print(f"\n📝 Text: {text[:80]}")
        result = model.analyze(text)
        print(f"   Tech zone : {result['tech_zone']} (score={result['tech_relevance_score']:.3f})")
        print(f"   Harmful   : {result['is_harmful']} — {result['primary_category']}")
        for category, score in result['scores'].items():
            if score > 0.3:
                marker = "🔴" if score > 0.7 else "🟡"
                print(f"   {marker} {category:15}: {score:.3f}")
        print(f"   Decision  : {'❌ BLOCK' if result['is_harmful'] else '✅ ALLOW'}")