"""
Stub ML analyzers used when heavy ML dependencies (torch, transformers, clip)
are not installed.  They perform basic keyword / heuristic analysis so the
server can still start, accept posts, and return sensible moderation results.
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class StubDistilBERTAnalyzer:
    """Keyword-based text analysis fallback (no torch required)"""

    def __init__(self):
        logger.warning(
            "ML dependencies not installed – using stub text analyzer "
            "(keyword-based only)"
        )
        self.flagged_patterns = {
            r'\b(hate|hates|hatred)\b': 'hate_speech',
            r'\b(kill|murder|death|die)\b': 'violence',
            r'\b(racist|racism)\b': 'discrimination',
            r'\b(sexist|sexism)\b': 'discrimination',
            r'\b(suicide|self.?harm)\b': 'self_harm',
            r'\b(porn|nsfw|explicit)\b': 'sexual_content',
            r'\b(scam|fraud|phishing)\b': 'scam',
            r'\b(terrorist|terrorism)\b': 'terrorism',
        }

    def analyze(self, text: str) -> Dict[str, Any]:
        flagged = self._extract_flagged_phrases(text)
        has_flagged = len(flagged) > 0
        return {
            "toxicity_score": 0.8 if has_flagged else 0.1,
            "confidence": 0.6 if has_flagged else 0.9,
            "category": flagged[0]["category"] if has_flagged else "safe",
            "flagged_phrases": flagged,
            "is_toxic": has_flagged,
            "using_stub": True,
        }

    def _extract_flagged_phrases(self, text: str) -> List[Dict[str, str]]:
        flagged: List[Dict[str, str]] = []
        text_lower = text.lower()
        for pattern, category in self.flagged_patterns.items():
            for match in re.finditer(pattern, text_lower):
                phrase = match.group()
                if phrase and len(phrase) > 2:
                    flagged.append({"phrase": phrase, "category": category})
        return flagged


class StubCLIPAnalyzer:
    """Passthrough image-text relevance stub (no torch/clip required)"""

    def __init__(self):
        logger.warning(
            "ML dependencies not installed – using stub CLIP analyzer "
            "(always returns relevant)"
        )

    def analyze(self, text: str, image_path: str) -> Dict[str, Any]:
        return {
            "similarity_score": 0.5,
            "is_relevant": True,
            "relevant_concepts": [],
            "mismatch_detected": False,
            "using_stub": True,
        }


class StubNSFWDetector:
    """Conservative NSFW stub (no torch required)"""

    def __init__(self):
        logger.warning(
            "ML dependencies not installed – using stub NSFW detector "
            "(always returns safe)"
        )

    def analyze(self, image_path: str) -> Dict[str, Any]:
        return {
            "nsfw_probability": 0.0,
            "is_nsfw": False,
            "primary_category": "safe",
            "confidence": 0.5,
            "category_probabilities": {},
            "explicit_content_detected": False,
            "using_stub": True,
        }
