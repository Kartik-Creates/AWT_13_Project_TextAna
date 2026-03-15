import re
from typing import List, Dict, Any, Set
import logging

from app.ml.text_normalizer import text_normalizer

logger = logging.getLogger(__name__)

class RuleEngine:
    """Rule-based content filtering with word-boundary matching.
    
    Uses \\b word-boundary regex to avoid false positives like
    'skill' matching 'kill' or 'studied' matching 'die'.
    """
    
    def __init__(self):
        # Core categories of harmful content — each keyword gets \\b boundaries
        self.banned_categories = {
            "drugs": [
                "drugs", "heroin", "cocaine", "weed", "meth",
                "fentanyl", "dealer", "drug dealer",
            ],
            "violence": [
                "kill you", "kill them", "kill him", "kill her",
                "kill everyone", "murder", "bomb", "shoot",
                "attack", "mass shooting", "gun violence",
            ],
            "harm": [
                "suicide", "self-harm", "self harm", "cutting myself",
                "hang myself", "end my life", "want to die",
            ],
            "offensive": [
                "nazi", "terrorist", "white supremacy",
            ],
            "promotional": [
                "earn money", "make money", "work from home",
                "zero effort", "no investment", "cash prize",
                "get rich quick",
            ],
        }
        
        # ── False-positive allowlist ──
        # Words/phrases that contain banned substrings but are innocent.
        # These are checked BEFORE keyword matching.
        self.allowlist_patterns = [
            # 'kill' inside safe words
            r'\bskill(?:s|ed|ful|fully)?\b',
            r'\bkill(?:er)?\s+(?:app|feature|design|look|outfit)\b',
            r'\boverkill\b',
            r'\bpainkiller(?:s)?\b',
            # 'die' inside safe words  
            r'\bdie-?cast(?:ing)?\b',
            r'\bstudied\b',
            r'\bsoldier(?:s)?\b',
            r'\baudience(?:s)?\b',
            r'\bdie(?:sel|t|tary|titian|tetics)\b',
            # 'death' inside safe words
            r'\bdeadline(?:s)?\b',
            # 'attack' in tech context
            r'\bheart\s+attack\b',
            r'\bpanic\s+attack\b',
            r'\basthma\s+attack\b',
            # 'bomb' in casual usage
            r'\bbomb(?:astic|shell)\b',
            r'\bphotobomb\b',
            # 'weed' in gardening context
            r'\bweed(?:s|ing|ed)?\s+(?:the|my|our|your|a)\s+(?:garden|yard|lawn|bed|field)\b',
            r'\bpull(?:ing)?\s+(?:out\s+)?weeds?\b',
            # 'shoot' in photography/sports
            r'\bphoto\s*shoot\b',
            r'\bshoot(?:ing)?\s+(?:a\s+)?(?:photo|video|film|movie|scene|hoop|basket)\b',
            # 'hate' in casual usage
            r'\bhate\s+(?:bugs?|mondays?|mornings?|traffic|homework|waiting|rain)\b',
            r'\bi\s+hate\s+(?:when|that|it\s+when|how)\b',
        ]
        
        # Pre-compile all patterns
        self._compiled_banned = {}
        for category, keywords in self.banned_categories.items():
            for kw in keywords:
                # Create word-boundary pattern
                escaped = re.escape(kw)
                pattern = rf'\b{escaped}\b'
                self._compiled_banned[re.compile(pattern, re.IGNORECASE)] = (kw, category)
        
        self._compiled_allowlist = [
            re.compile(p, re.IGNORECASE) for p in self.allowlist_patterns
        ]

        # Suspicious URL patterns
        self.url_patterns = [
            r'bit\.ly', r'goo\.gl', r't\.co', r'tinyurl\.com', r'is\.gd',
            r'buff\.ly', r't\.me', r'crypto', r'free-prizes'
        ]
        
        # Spam patterns
        self.spam_patterns = [
            r'(.)\1{4,}',           # Repeated characters (aaaaa)
            r'[A-Z]{10,}',          # Long all caps
            r'\b(viagra|casino|lottery|winner|congratulations|prize)\b'
        ]
        
        self.url_regex = re.compile('|'.join(self.url_patterns), re.IGNORECASE)
        self.spam_regex = re.compile('|'.join(self.spam_patterns), re.IGNORECASE)

    def check_rules(self, text: str) -> Dict[str, Any]:
        """Check text against all rules."""
        text_stripped = text.strip()
        
        results = {
            "banned_keywords": [],
            "keyword_categories": [],
            "suspicious_urls": [],
            "spam_detected": False,
            "violations": [],
        }
        
        if not text_stripped:
            results["rule_score"] = 0.0
            return results
        
        # ── Step 0: Find allowlisted spans ──
        # Mask out portions of text that match the allowlist so they don't
        # trigger banned-keyword rules.
        masked_text = text_stripped
        for pattern in self._compiled_allowlist:
            masked_text = pattern.sub(lambda m: '_' * len(m.group()), masked_text)
        
        # ── Step 1: Check banned keywords (word-boundary, on masked text) ──
        for pattern, (keyword, category) in self._compiled_banned.items():
            if pattern.search(masked_text):
                results["banned_keywords"].append(keyword)
                results["keyword_categories"].append(category)
                results["violations"].append(f"keyword:{keyword}")
        
        # ── Step 2: Check suspicious URLs ──
        urls = self.url_regex.findall(text_stripped.lower())
        if urls:
            results["suspicious_urls"] = urls
            results["violations"].append("suspicious_url")
        
        # ── Step 3: Check spam ──
        spam_matches = self.spam_regex.findall(text_stripped)
        if spam_matches:
            if len(spam_matches) > 1 or any(
                kw in text_stripped.lower()
                for kw in ["earn money", "winner", "congratulations", "cash prize"]
            ):
                results["spam_detected"] = True
                results["violations"].append("spam")
        # ── Step 4: Check Hindi/Hinglish abuse ──
        hindi_check = text_normalizer.detect_hindi_abuse(text_stripped)
        if hindi_check["has_hindi_abuse"]:
            for word in hindi_check["matched_words"]:
                results["banned_keywords"].append(word)
                results["keyword_categories"].append("hindi_abuse")
                results["violations"].append(f"hindi_abuse:{word}")
        results["hindi_detection"] = hindi_check
        
        # ── Score ──
        unique_violations = len(set(results["violations"]))
        results["rule_score"] = min(unique_violations * 0.5, 1.0)
        
        return results