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
        # ── Hindi Gali Mappings (variations and spellings) ──
        self.hindi_galis = {
            # Core abusive words with all variations
            "madarchod": [
                r'madar?ch?od', r'madar ?chod', r'madar ?ch?od', r'mdrchod',
                r'mdr ?chod', r'motherchod', r'mother ?chod', r'motherch?od',
                r'mdrch?d', r'madarjaat', r'madar ?jaat', r'madar ?zat',
                r'mc', r'm\.?c\.?', r'm\s*c'
            ],
            "bhenchod": [
                r'b(?:e|o|a|h)?henchod', r'be?hen ?chod', r'b(?:e|o)hn ?chod',
                r'b(?:e|o)han ?chod', r'bc', r'b\.?c\.?', r'b\s*c', r'b\.c',
                r'behench?d', r'bhen ?ch?d', r'sisterfucker', r'sister ?fucker'
            ],
            "chutiya": [
                r'chutiya', r'chutiye', r'chut?iya', r'chut?iye', r'chutiya',
                r'choot?iya', r'choot?iye', r'chut?ya', r'choot?ya',
                r'chut?ye', r'choot?ye', r'ch*t*iya'
            ],
            "gandu": [
                r'gandu', r'gand?u', r'gandoo', r'gand?oo', r'gandhu',
                r'gand?hu', r'gandu', r'gaa?ndu', r'gand ?u'
            ],
            "randi": [
                r'randi', r'rand?i', r'randee', r'rand?ee', r'r*ndi',
                r'randi ?ka', r'randi ?ke', r'randi ?ki'
            ],
            "bhosdi": [
                r'bhosdi', r'bhosd?i', r'bhosdike', r'bhosdi ?ke',
                r'bhosd?ike', r'bhosda', r'bhosd?a', r'bhosd?a'
            ],
            "kutta": [
                r'kutta', r'kutta ?ka', r'kutte', r'kutte ?ka',
                r'kutia', r'kutiya', r'kut?iya', r'kut?ia'
            ],
            "chinal": [
                r'chinal', r'ch?inal', r'chinnal', r'ch?innal',
                r'chilnal', r'ch?ilnal'
            ],
            "harami": [
                r'harami', r'haram?i', r'hara?mi', r'haram ?i',
                r'haramza?de', r'haramzade', r'haram ?zade'
            ],
            "sala": [
                r'sala', r'sa?la', r'saale', r'sa?le', r'saal?e'
            ],
            "lavde": [
                r'lavde', r'lavd?e', r'lawde', r'lawd?e', r'l*avde',r'lode', r'lod?e',r'laude', r'laud?e',r'lo?de', r'la?ude',r'lvde', r'lv?de',r'la?vde', r'lo?vde'
            ],
            "chod": [
                r'chod', r'ch?od', r'chodd?', r'ch?odd?',
                r'ch*d', r'fuck', r'f\*ck', r'f\*\*k', r'f.u.c.k',
                r'fuk', r'fak', r'phuck'
            ],
            "lund": [
                r'lund', r'l*nd', r'lun?d', r'lound', r'lond'
            ],
            "gaand": [
                r'gaand', r'gaa?nd', r'gand', r'g\*nd', r'ass'
            ],
            "tatte": [
                r'tatte', r'tat?te', r't*tte', r'balls'
            ],
            "bsdk": [
                r'bsdk', r'b\.?s\.?d\.?k\.?', r'b\s*s\s*d\s*k', r'b s d k',
                r'behen ke', r'bahan ke', r'bhen ke'
            ]
        }
        
        # Core categories of harmful content — each keyword gets \b boundaries
        self.banned_categories = {
            "drugs": [
                "drugs", "heroin", "cocaine", "weed", "meth",
                "fentanyl", "dealer", "drug dealer", "coke", "crack",
                "mdma", "ecstasy", "lsd", "acid", "shrooms", "mushrooms",
                "opium", "morphine", "oxy", "percocet", "xanax", "valium",
                "diazepam", "amphetamine", "methamphetamine", "ice",
                "crystal meth", "dope", "smack", "skunk", "ganja",
                "bhang", "charas", "hash", "hashish", "weed", "pot",
                "marijuana", "cannabis", "thc", "cbd", "vape", "vaping",
                "nicotine", "tobacco", "cigarette", "cigar"
            ],
            "violence": [
                "kill you", "kill them", "kill him", "kill her",
                "kill everyone", "murder", "bomb", "shoot",
                "attack", "mass shooting", "gun violence", "shoot up",
                "stab", "stabbing", "beat up", "beat you", "beat him",
                "beat her", "slap", "punch", "kick", "torture",
                "execute", "execution", "assassinate", "assassination",
                "terrorist", "terrorism", "jihad", "martyr", "martyrdom",
                "explode", "explosion", "blast", "bombing", "suicide bomb"
            ],
            "harm": [
                "suicide", "self-harm", "self harm", "cutting myself",
                "hang myself", "end my life", "want to die", "kill myself",
                "take my life", "end it all", "end it now", "better off dead",
                "no reason to live", "worthless", "want to disappear",
                "jump off", "jump from", "overdose", "od on", "rope",
                "pills", "sleep forever", "never wake up"
            ],
            "offensive": [
                "nazi", "terrorist", "white supremacy", "kkk", "ku klux",
                "hitler", "fascist", "neo-nazi", "racial slurs", "racist",
                "homophobic", "transphobic", "xenophobic", "islamophobic",
                "antisemitic", "anti-semitic", "jew hating", "black hating"
            ],
            "sexual": [
                "nude", "nudes", "pics", "photos", "send pics", "send nudes",
                "sext", "sexting", "sex tape", "private video", "leaked",
                "leak", "exposed", "expose", "blackmail", "coerce", "forced",
                "creampie", "slut", "whore", "c*ck", "d*ck", "pussy",
                "tits", "boobs", "ass", "booty", "anal", "oral",
                "blowjob", "handjob", "fuck", "fucking", "suck",
                "rape", "raped", "raping", "molest", "molested"
            ],
            "promotional": [
                "earn money", "make money", "work from home",
                "zero effort", "no investment", "cash prize",
                "get rich quick", "bitcoin", "crypto", "cryptocurrency",
                "investment", "invest now", "guaranteed returns",
                "double your money", "money back", "profit",
                "referral", "refer and earn", "sign up bonus",
                "free money", "free cash", "free bitcoin",
                "click here", "link in bio", "link in profile",
                "dm me", "message me", "whatsapp me", "telegram"
            ],
        }
        
        # ── False-positive allowlist ──
        self.allowlist_patterns = [
            # 'kill' inside safe words
            r'\bskill(?:s|ed|ful|fully)?\b',
            r'\bkill(?:er)?\s+(?:app|feature|design|look|outfit|shot)\b',
            r'\boverkill\b',
            r'\bpainkiller(?:s)?\b',
            # 'die' inside safe words  
            r'\bdie-?cast(?:ing)?\b',
            r'\bstudied\b',
            r'\bsoldier(?:s)?\b',
            r'\baudience(?:s)?\b',
            r'\bdie(?:sel|t|tary|titian|tetics)\b',
            r'\bdied(?:re)?\b',
            r'\bdies\b',
            # 'death' inside safe words
            r'\bdeadline(?:s)?\b',
            r'\bdeadwood\b',
            # 'attack' in tech/medical context
            r'\bheart\s+attack\b',
            r'\bpanic\s+attack\b',
            r'\basthma\s+attack\b',
            r'\banxiety\s+attack\b',
            # 'bomb' in casual usage
            r'\bbomb(?:astic|shell)\b',
            r'\bphotobomb\b',
            r'\b(?:the|this|that)\s+bomb\b',
            # 'weed' in gardening context
            r'\bweed(?:s|ing|ed)?\s+(?:the|my|our|your|a)\s+(?:garden|yard|lawn|bed|field|plant|patch)\b',
            r'\bpull(?:ing)?\s+(?:out\s+)?weeds?\b',
            r'\bweed\s+(?:killer|control|removal)\b',
            # 'shoot' in photography/sports
            r'\bphoto\s*shoot\b',
            r'\bshoot(?:ing)?\s+(?:a\s+)?(?:photo|video|film|movie|scene|hoop|basket|ball|goal)\b',
            r'\bshoot(?:er)?\s+(?:game|games)\b',
            # 'hate' in casual usage
            r'\bhate\s+(?:bugs?|mondays?|mornings?|traffic|homework|waiting|rain|cold|heat|spiders|snakes)\b',
            r'\bi\s+hate\s+(?:when|that|it\s+when|how)\b',
            # 'drug' in medical context
            r'\bdrug\s+(?:store|shop|pharmacy|prescription|medicine|medication|treatment|therapy)\b',
            r'\bdrugs?\s+(?:for|to)\s+(?:pain|illness|disease|condition|symptom)\b',
            r'\b(?:prescription|medicinal|generic)\s+drugs?\b',
            # 'cocaine' in medical/dental context
            r'\bcocaine\s+(?:anesthesia|anesthetic|numbing|dental|medical)\b',
            r'\b(?:dental|medical)\s+cocaine\b',
        ]
        
        # Compile all patterns
        self._compiled_banned = {}
        for category, keywords in self.banned_categories.items():
            for kw in keywords:
                escaped = re.escape(kw)
                pattern = rf'\b{escaped}\b'
                self._compiled_banned[re.compile(pattern, re.IGNORECASE)] = (kw, category)
        
        # Compile Hindi gali patterns
        self._compiled_hindi = []
        for category, patterns in self.hindi_galis.items():
            for pattern in patterns:
                self._compiled_hindi.append((re.compile(pattern, re.IGNORECASE), category))
        
        self._compiled_allowlist = [
            re.compile(p, re.IGNORECASE) for p in self.allowlist_patterns
        ]

        # Suspicious URL patterns
        self.url_patterns = [
            r'bit\.ly', r'goo\.gl', r't\.co', r'tinyurl\.com', r'is\.gd',
            r'buff\.ly', r't\.me', r'crypto', r'free-prizes', r'shorturl',
            r'ow\.ly', r'short\.link', r'rb\.gy', r'cutt\.ly', r'shorten',
            r'tiny\.cc', r'tr\.im', r'v\.gd', r'cli\.gs', r'shrinke\.me'
        ]
        
        # Spam patterns
        self.spam_patterns = [
            r'(.)\1{4,}',           # Repeated characters (aaaaa)
            r'[A-Z]{10,}',          # Long all caps
            r'\b(viagra|casino|lottery|winner|congratulations|prize|won\s+\d+|\$\d+|\d+\$)\b',
            r'\b(click here|subscribe|share|like and share|comment below)\b',
            r'\b(free|cheap|discount|offer|limited time|act now|don\'t miss)\b'
        ]
        
        self.url_regex = re.compile('|'.join(self.url_patterns), re.IGNORECASE)
        self.spam_regex = re.compile('|'.join(self.spam_patterns), re.IGNORECASE)

    def normalize_text(self, text: str) -> str:
        """Normalize text to catch leetspeak and variations"""
        # Replace common leetspeak
        leet_map = {
            '0': 'o', '1': 'i', '2': 'z', '3': 'e', '4': 'a',
            '5': 's', '6': 'b', '7': 't', '8': 'b', '9': 'g',
            '@': 'a', '$': 's', '!': 'i', '+': 't', '|': 'i'
        }
        
        normalized = text.lower()
        for leet, char in leet_map.items():
            normalized = normalized.replace(leet, char)
        
        # Remove special characters
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized

    def check_rules(self, text: str) -> Dict[str, Any]:
        """Check text against all rules."""
        text_stripped = text.strip()
        normalized = self.normalize_text(text_stripped)
        
        results = {
            "banned_keywords": [],
            "keyword_categories": [],
            "suspicious_urls": [],
            "spam_detected": False,
            "violations": [],
            "hindi_detection": {"has_hindi_abuse": False, "matched_words": []}
        }
        
        if not text_stripped:
            results["rule_score"] = 0.0
            return results
        
        # ── Step 0: Find allowlisted spans ──
        masked_text = text_stripped
        for pattern in self._compiled_allowlist:
            masked_text = pattern.sub(lambda m: '_' * len(m.group()), masked_text)
        
        masked_normalized = normalized
        for pattern in self._compiled_allowlist:
            masked_normalized = pattern.sub(lambda m: '_' * len(m.group()), masked_normalized)
        
        # ── Step 1: Check banned keywords ──
        for pattern, (keyword, category) in self._compiled_banned.items():
            if pattern.search(masked_text) or pattern.search(masked_normalized):
                results["banned_keywords"].append(keyword)
                results["keyword_categories"].append(category)
                results["violations"].append(f"keyword:{keyword}")
        
        # ── Step 2: Check Hindi galis ──
        hindi_matched = []
        for pattern, category in self._compiled_hindi:
            if pattern.search(masked_text) or pattern.search(masked_normalized):
                hindi_matched.append(category)
                if category not in results["keyword_categories"]:
                    results["keyword_categories"].append(category)
                results["violations"].append(f"hindi_abuse:{category}")
        
        if hindi_matched:
            results["hindi_detection"]["has_hindi_abuse"] = True
            results["hindi_detection"]["matched_words"] = list(set(hindi_matched))
            if "bhenchod" in hindi_matched:
                results["banned_keywords"].append("bc")
            if "madarchod" in hindi_matched:
                results["banned_keywords"].append("mc")
            if "bsdk" in hindi_matched:
                results["banned_keywords"].append("bsdk")
        
        # ── Step 3: Check suspicious URLs ──
        urls = self.url_regex.findall(text_stripped.lower())
        if urls:
            results["suspicious_urls"] = list(set(urls))
            results["violations"].append("suspicious_url")
        
        # ── Step 4: Check spam ──
        spam_matches = self.spam_regex.findall(text_stripped)
        if spam_matches:
            spam_count = len(spam_matches)
            if spam_count > 1 or any(
                kw in text_stripped.lower()
                for kw in ["earn money", "winner", "congratulations", "cash prize", "free", "click here"]
            ):
                results["spam_detected"] = True
                results["violations"].append("spam")
        
        # ── Step 5: Check Hindi/Hinglish abuse via normalizer ──
        hindi_check = text_normalizer.detect_hindi_abuse(text_stripped)
        if hindi_check["has_hindi_abuse"]:
            for word in hindi_check["matched_words"]:
                results["banned_keywords"].append(word)
                if "hindi_abuse" not in results["keyword_categories"]:
                    results["keyword_categories"].append("hindi_abuse")
                results["violations"].append(f"hindi_abuse:{word}")
            results["hindi_detection"] = hindi_check
        
        # ── FIXED Score calculation ──
        unique_violations = len(set(results["violations"]))
        
        # Base score - each violation adds more weight
        if unique_violations == 0:
            results["rule_score"] = 0.0
        elif unique_violations == 1:
            results["rule_score"] = 0.6  # Single violation should block!
        elif unique_violations == 2:
            results["rule_score"] = 0.8
        else:
            results["rule_score"] = 1.0
        
        # Apply severity multiplier for dangerous categories
        severity_multiplier = 1.0
        if "violence" in results["keyword_categories"]:
            severity_multiplier = 1.3
        if "harm" in results["keyword_categories"]:
            severity_multiplier = 1.3
        if "sexual" in results["keyword_categories"]:
            severity_multiplier = 1.2
        if "hindi_abuse" in results["keyword_categories"]:
            severity_multiplier = 1.2
        
        results["rule_score"] = min(results["rule_score"] * severity_multiplier, 1.0)
        
        # Log for debugging
        if results["rule_score"] > 0:
            logger.info(f"📊 Rule score: {results['rule_score']:.2f} (violations={unique_violations}, categories={results['keyword_categories']})")
        
        return results