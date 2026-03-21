import re
from typing import List, Dict, Any, Set, Tuple
import logging

from app.ml.text_normalizer import text_normalizer

logger = logging.getLogger(__name__)

class RuleEngine:
    """Rule-based content filtering with word-boundary matching and CONTEXT AWARENESS.
    
    Uses \\b word-boundary regex to avoid false positives like
    'skill' matching 'kill' or 'studied' matching 'die'.
    Now with context analysis to distinguish harmful vs safe usage.
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
                r'behench?d', r'bhen ?ch?d', r'sisterfucker', r'sister ?fucker',
                r'bokachoda', r'bokkachoda', r'bok\*choda'
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
        
        # ── ENHANCED False-positive allowlist (covers all common false positives) ──
        self.allowlist_patterns = [
            # ========== "KILL" FAMILY ==========
            r'\bskill(?:s|ed|ful|fully|set|level|gap|building|development|assessment)?\b',
            r'\bkill(?:er)?\s+(?:app|feature|design|look|outfit|shot|session|workout|game|time|joy|stress|anxiety|process|thread|server|session|connection|task|job|query|command|script|program|execution|running|feature|function|notification|alert|file|folder|directory|data|record)\b',
            r'\boverkill\b',
            r'\bpainkiller(?:s)?\b',
            r'\btimekiller(?:s)?\b',
            
            # ========== "DIE" FAMILY ==========
            r'\bdiscipline\w*\b',  # discipline, disciplined, disciplines, disciplining
            r'\bdepends?\s+(?:on|upon)\b',  # CRITICAL - contains "die"
            r'\bstudied\b',
            r'\bstudies\b',
            r'\bstudying\b',
            r'\bsoldier(?:s)?\b',
            r'\baudience(?:s)?\b',
            r'\bdie(?:sel|t|tary|titian|tetics|tary|tetic|tetics|t|\w*?tary?)?\b',
            r'\bdied(?:re)?\b',
            r'\bdies\b',
            r'\bdie-?cast(?:ing)?\b',
            
            # ========== "DEATH" FAMILY ==========
            r'\bdeadline(?:s)?\b',
            r'\bdeadwood\b',
            r'\bdeadlock(?:s)?\b',
            r'\bdeadpan\b',
            r'\bdeadbeat\b',
            r'\bdeadend\b',
            
            # ========== "ATTACK" FAMILY ==========
            r'\bheart\s+attack\b',
            r'\bpanic\s+attack\b',
            r'\basthma\s+attack\b',
            r'\banxiety\s+attack\b',
            r'\bcoughing\s+attack\b',
            r'\bsneezing\s+attack\b',
            
            # ========== "BOMB" FAMILY ==========
            r'\bbomb(?:astic|shell)\b',
            r'\bphotobomb\b',
            r'\b(?:the|this|that)\s+bomb\b',
            r'\bbomb\s+(?:site|location|area)\b',
            
            # ========== "WEED" FAMILY ==========
            r'\bweed(?:s|ing|ed)?\s+(?:the|my|our|your|a)\s+(?:garden|yard|lawn|bed|field|plant|patch)\b',
            r'\bpull(?:ing)?\s+(?:out\s+)?weeds?\b',
            r'\bweed\s+(?:killer|control|removal|whacker|trimmer)\b',
            
            # ========== "SHOOT" FAMILY ==========
            r'\bphoto\s*shoot\b',
            r'\bshoot(?:ing)?\s+(?:a\s+)?(?:photo|video|film|movie|scene|hoop|basket|ball|goal|game|match|session)\b',
            r'\bshoot(?:er)?\s+(?:game|games|tournament)\b',
            
            # ========== "HATE" FAMILY ==========
            r'\bhate\s+(?:bugs?|mondays?|mornings?|traffic|homework|waiting|rain|cold|heat|spiders|snakes|vegetables|exercise)\b',
            r'\bi\s+hate\s+(?:when|that|it\s+when|how)\b',
            r'\bhate\s+(?:to|having)\s+(?:wait|see|hear|do|deal)\b',
            
            # ========== "DRUG" FAMILY ==========
            r'\bdrug\s+(?:store|shop|pharmacy|prescription|medicine|medication|treatment|therapy|interaction|resistance)\b',
            r'\bdrugs?\s+(?:for|to)\s+(?:pain|illness|disease|condition|symptom|allergy|infection)\b',
            r'\b(?:prescription|medicinal|generic|over-the-counter)\s+drugs?\b',
            
            # ========== "COCAINE" FAMILY ==========
            r'\bcocaine\s+(?:anesthesia|anesthetic|numbing|dental|medical)\b',
            r'\b(?:dental|medical|topical)\s+cocaine\b',
            
            # ========== "ASS" FAMILY ==========
            r'\bclassic\b',
            r'\bpassport\b',
            r'\bassassin\b',
            r'\bassistant\b',
            r'\bassociate\b',
            r'\bassembly\b',
            r'\bassert\b',
            r'\bassess\b',
            r'\basset\b',
            r'\bassign\b',
            r'\bassist\b',
            
            # ========== "BEAT" FAMILY - FIX FOR "beats shortcuts" ==========
            r'\bbeats?\s+(?:shortcuts|the|everything|all|competition|records?|goals|targets|odds|system)\b',
            r'\bbeats?\s+(?:the\s+game|level|boss)\b',
            r'\b(?:heart|drum|music)\s+beats?\b',
            r'\bbeat\s+(?:around\s+the\s+bush)\b',
            
            # ========== "CUT" FAMILY ==========
            r'\bshortcuts?\b',
            r'\bcut\s+(?:costs|expenses|time|effort|corners?)\b',
            r'\bcut\s+(?:the|a)\s+(?:cake|bread|vegetables|fruit|paper|fabric)\b',
            r'\bcut\s+(?:in\s+line|ahead|off)\b',
            
            # ========== EDUCATIONAL/TECH CONTEXTS ==========
            r'\b(?:learn|study|practice|master|develop|improve|build|create|design|code|program|write|read|understand|analyze|research)\s+(?:skill|discipline|technique|method|approach|strategy|habit|routine)\b',
            r'\b(?:coding|programming|development|software|engineering)\s+(?:skill|discipline|practice)\b',
            r'\blearning\s+(?:new|curve|process|experience)\b',
            r'\bpracticing\s+(?:daily|regularly|consistently)\b',
            r'\b(?:consistency|dedication|hard\s+work)\s+(?:is|beats|wins)\b',
            
            # ========== GENERAL SAFE WORDS ==========
            r'\b(?:skill|skills|skilled|skillful)\b',
            r'\b(?:discipline|disciplined|disciplines)\b',
            r'\b(?:practice|practicing|practiced)\b',
            r'\b(?:learn|learning|learned)\b',
            r'\b(?:study|studying|studies|studied)\b',
            r'\b(?:soldier|soldiers)\b',
            r'\b(?:audience|audiences)\b',
            r'\b(?:diet|dietary|dietitian)\b',
            r'\b(?:deadline|deadlines)\b',
            r'\b(?:technology|technologies)\b',
            r'\b(?:consistency|consistent|consistently)\b',
            r'\b(?:success|successful|succeed)\b',
            r'\b(?:coding|programming|developer|development)\b',
            r'\b(?:goals|targets|objectives)\b',
            r'\bkey\s+(?:is|to|factor|element|component)\b',
        ]
        
        # ========== CONTEXT-AWARE PATTERNS ==========
        # These detect HARMFUL usage based on surrounding context
        
        self.harmful_context_patterns = {
            # Self-harm - requires personal context
            "self_harm": [
                (r'\b(?:i|im|i am|i will|i want to|i need to|i should|im going to)\s+(?:kill|end|take)\s+(?:myself|my life|my own life)\b', 0.95),
                (r'\b(?:want to|going to|plan to|thinking about)\s+(?:die|end it|kill myself|take my life)\b', 0.9),
                (r'\b(?:better off dead|no reason to live|worthless|want to disappear)\b', 0.85),
                (r'\b(?:cutting|hanging|jumping|overdosing)\s+(?:myself|myself|from)\b', 0.95),
                (r'\b(?:rope|pills|bridge|tall building)\s+(?:to end it|to kill myself)\b', 0.9),
            ],
            
            # Violence - requires target
            "violence": [
                (r'\b(?:i will|im going to|gonna|want to)\s+(?:kill|murder|shoot|stab|beat up|attack)\s+(?:you|him|her|them|someone|anyone)\b', 0.95),
                (r'\b(?:threat|warning|come for|hunt down|find you)\b', 0.85),
                (r'\b(?:bomb|shoot|attack)\s+(?:the|a|their)\s+(?:school|office|place|building|people|crowd)\b', 1.0),
            ],
            
            # Threats - direct and specific
            "threats": [
                (r'\b(?:i will|im going to|gonna)\s+(?:make sure|ensure)\s+(?:you|they)\s+(?:pay|suffer|regret)\b', 0.85),
                (r'\b(?:one more word|if you|dont you)\s+(?:ill|i will)\s+(?:kill|hurt|destroy)\b', 0.9),
                (r'\b(?:you(?:'')?re dead|you(?:'')?re finished|your last day)\b', 0.9),
            ],
        }
        
        # Safe contexts that override harmful detection
        self.safe_context_patterns = [
            # Tech/Programming contexts
            (r'\b(?:kill|die|death|dead)\s+(?:process|thread|server|session|connection|app|service|task|job|query|command|script|program|execution|running)\b', "tech"),
            (r'\b(?:kill|stop|terminate)\s+(?:process|service|application|task)\b', "tech"),
            (r'\b(?:kill|disable|turn off)\s+(?:feature|function|notification|alert|setting)\b', "tech"),
            (r'\b(?:kill|remove|delete)\s+(?:file|folder|directory|data|record|entry)\b', "tech"),
            (r'\b(?:dead|dying)\s+(?:code|line|branch|variable|function|method)\b', "tech"),
            (r'\b(?:death|dead)\s+(?:of|for)\s+(?:a|the)\s+(?:product|project|technology|language|framework)\b', "tech"),
            
            # Gaming contexts
            (r'\b(?:kill|die|death)\s+(?:in game|in the game|character|player|boss|enemy|creep|mob|npc)\b', "gaming"),
            (r'\b(?:pvp|pve|raid|dungeon|arena|match|round|tournament)\s+(?:kill|death)\b', "gaming"),
            (r'\b(?:kill|death)\s+(?:streak|count|ratio|record|achievement|stat)\b', "gaming"),
            
            # Entertainment contexts
            (r'\b(?:movie|show|film|series|book|novel|story|plot)\s+(?:about|where|when)\s+(?:kill|death|die|murder)\b', "entertainment"),
            (r'\b(?:kill|death|die|murder)\s+(?:scene|moment|plot|storyline|character|actor|actress)\b', "entertainment"),
            
            # Educational/Motivational contexts
            (r'\b(?:learn|study|practice|master|improve|develop)\s+(?:skill|discipline|technique|method)\b', "educational"),
            (r'\b(?:skill|discipline|practice)\s+(?:is|are|makes|helps|leads to)\s+(?:important|key|crucial|essential)\b', "educational"),
            
            # News/Reporting contexts
            (r'\b(?:reported|news|article|headline|source|according to)\s+(?:about|on)\s+(?:death|kill|murder)\b', "news"),
            (r'\b(?:police|authorities|officials|investigators)\s+(?:investigating|probing|looking into)\s+(?:death|kill)\b', "news"),
            
            # Medical/Health contexts
            (r'\b(?:die|death|kill)\s+(?:from|due to|caused by)\s+(?:disease|illness|cancer|heart|stroke|infection)\b', "medical"),
            (r'\b(?:die|death)\s+(?:rate|statistics|percentage|mortality|survival)\b', "medical"),
            (r'\b(?:kill|die)\s+(?:bacteria|cells|virus|germs|infection|pathogen)\b', "medical"),
            
            # Casual/Slang contexts
            (r'\b(?:im|i am|i''m)\s+(?:dying|dead)\s+(?:of|from)\s+(?:laughter|laugh|funny|joke|hilarious)\b', "casual"),
            (r'\b(?:kill|die)\s+(?:me|it|them|inside)\s+(?:laughing|funny|hilarious|with laughter)\b', "casual"),
            (r'\b(?:that|this|it)\s+(?:kills?|dies?)\s+(?:me|it)\b', "casual"),
        ]
        
        # Safe words that should never be blocked
        self.safe_words = {
            'skill', 'skills', 'skilled', 'skillful',
            'discipline', 'disciplined', 'disciplines',
            'practice', 'practicing', 'practiced',
            'learn', 'learning', 'learned',
            'study', 'studying', 'studies', 'studied',
            'soldier', 'soldiers',
            'audience', 'audiences',
            'diet', 'dietary', 'dietitian',
            'deadline', 'deadlines',
            'classic', 'passport', 'assassin', 'assistant', 'associate',
            'assembly', 'assert', 'assess', 'asset', 'assign', 'assist',
            'technology', 'technologies', 'consistency', 'consistent', 'consistently',
            'success', 'successful', 'succeed', 'coding', 'programming',
            'developer', 'development', 'goals', 'targets', 'objectives'
        }
        
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
        
        # FIXED: Spam patterns - MUCH MORE PRECISE to avoid false positives
        self.spam_patterns = [
            # Repeated characters - only 7+ consecutive repeats (extreme spam)
            r'(.)\1{7,}',
            
            # All caps spam - only if multiple words in caps with spam content
            r'(?:[A-Z]{5,}\s+){2,}(?:FREE|WINNER|CLICK|NOW|BUY|GET)',
            
            # Spam keywords with action verbs
            r'\b(viagra|casino|lottery)\s+(?:click|visit|buy|order|now)\b',
            r'\b(winner|congratulations|prize)\s+(?:you|click|claim|get)\b',
            
            # Money spam patterns
            r'\b(?:earn|make|get)\s+(?:money|cash|profit)\s+(?:fast|quick|easy|now)\b',
            r'\b(?:work from home|no investment|get rich quick|double your money)\b',
            
            # URL shortener spam
            r'(?:bit\.ly|tinyurl|goo\.gl|t\.co)\s+(?:free|money|cash|prize|bonus)',
            
            # Call to action spam with multiple exclamations
            r'(?:click here|subscribe now|share now|comment below)\s*[!]{2,}',
            
            # Multiple money symbols (spam indicator)
            r'(?:[\$\€\£\₹]\s*\d+[\s,]*){3,}',
            
            # Excessive emojis (spam indicator)
            r'[😀-🙏]{6,}',
        ]
        
        self.url_regex = re.compile('|'.join(self.url_patterns), re.IGNORECASE)
        self.spam_regex = re.compile('|'.join(self.spam_patterns), re.IGNORECASE)
        
        logger.info("✅ Rule Engine initialized with enhanced context awareness")

    def _analyze_context(self, text: str, matched_word: str, category: str) -> Dict[str, Any]:
        """
        Analyze context around a matched word to determine if usage is harmful.
        
        Returns:
            {
                'is_harmful': bool,
                'confidence': float,
                'context_type': str,
                'reasoning': str
            }
        """
        text_lower = text.lower()
        
        # First check if the matched word itself is in safe words list
        if matched_word.lower() in self.safe_words:
            return {
                'is_harmful': False,
                'confidence': 0.95,
                'context_type': 'safe_word',
                'reasoning': f"'{matched_word}' is in safe words list"
            }
        
        # Step 1: Check for safe contexts first (override)
        for pattern, context_type in self.safe_context_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                # Get surrounding context (30 chars before and after)
                start = max(0, match.start() - 30)
                end = min(len(text_lower), match.end() + 30)
                context = text_lower[start:end]
                
                if matched_word.lower() in context:
                    return {
                        'is_harmful': False,
                        'confidence': 0.9,
                        'context_type': context_type,
                        'reasoning': f"Found in safe {context_type} context"
                    }
        
        # Step 2: Check for harmful contexts
        for harm_category, patterns in self.harmful_context_patterns.items():
            for pattern, weight in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    start = max(0, match.start() - 30)
                    end = min(len(text_lower), match.end() + 30)
                    context = text_lower[start:end]
                    
                    if matched_word.lower() in context:
                        return {
                            'is_harmful': True,
                            'confidence': weight,
                            'context_type': harm_category,
                            'reasoning': f"Found in harmful {harm_category} context"
                        }
        
        # Step 3: Check surrounding words for educational context
        words = text_lower.split()
        for i, word in enumerate(words):
            if matched_word.lower() in word:
                start = max(0, i - 5)
                end = min(len(words), i + 6)
                surrounding = words[start:end]
                
                # Educational verbs indicate safe usage
                educational_verbs = ['learn', 'study', 'practice', 'master', 'develop', 'improve', 'build', 'create']
                if any(verb in surrounding for verb in educational_verbs):
                    return {
                        'is_harmful': False,
                        'confidence': 0.85,
                        'context_type': 'educational',
                        'reasoning': f"Found near educational verbs"
                    }
                
                # Harmful personal pronouns with harmful verbs
                harmful_pronouns = ['i', 'me', 'myself', 'you', 'yourself']
                harmful_verbs = ['want', 'need', 'will', 'going', 'plan', 'threat']
                if any(pronoun in surrounding for pronoun in harmful_pronouns):
                    if any(verb in surrounding for verb in harmful_verbs):
                        return {
                            'is_harmful': True,
                            'confidence': 0.8,
                            'context_type': 'personal_threat',
                            'reasoning': f"Personal context with harmful intent"
                        }
        
        # Step 4: Default based on category
        # If it's in violence/harm category but no harmful context, assume safe
        if category in ["violence", "harm"]:
            return {
                'is_harmful': False,
                'confidence': 0.6,
                'context_type': 'neutral',
                'reasoning': f"No harmful context detected for {category} word"
            }
        
        # Default to suspicious (fail-safe)
        return {
            'is_harmful': True,
            'confidence': 0.5,
            'context_type': 'unknown',
            'reasoning': "No clear context, defaulting to suspicious"
        }

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
        """Check text against all rules with CONTEXT AWARENESS."""
        text_stripped = text.strip()
        normalized = self.normalize_text(text_stripped)
        
        results = {
            "banned_keywords": [],
            "keyword_categories": [],
            "suspicious_urls": [],
            "spam_detected": False,
            "violations": [],
            "hindi_detection": {"has_hindi_abuse": False, "matched_words": []},
            "context_analysis": {}  # Track context decisions
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
        
        # ── Step 1: Check banned keywords WITH CONTEXT ──
        for pattern, (keyword, category) in self._compiled_banned.items():
            matches = pattern.finditer(masked_text)
            for match in matches:
                matched_word = match.group()
                
                # Analyze context
                context_analysis = self._analyze_context(masked_text, matched_word, category)
                
                # Only flag if harmful in context
                if context_analysis['is_harmful']:
                    results["banned_keywords"].append(keyword)
                    results["keyword_categories"].append(category)
                    results["violations"].append(f"keyword:{keyword}")
                    results["context_analysis"][keyword] = context_analysis
                    logger.info(f"⚠️ Flagged '{keyword}' - {context_analysis['reasoning']}")
                else:
                    logger.debug(f"✅ Ignored safe usage of '{keyword}' - {context_analysis['reasoning']}")
        
        # ── Step 2: Check Hindi galis (these are abusive and should always be blocked) ──
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
        
        # ── Step 4: Check spam - NOW WITH PRECISE PATTERNS ──
        spam_matches = self.spam_regex.findall(text_stripped)
        if spam_matches:
            # Only flag as spam if it's clearly spam (not just a single match)
            # For motivational text, this won't trigger
            results["spam_detected"] = True
            results["violations"].append("spam")
            logger.debug(f"Spam matches found: {spam_matches[:3]}")
        
        # ── Step 5: Check Hindi/Hinglish abuse via normalizer ──
        try:
            hindi_check = text_normalizer.detect_hindi_abuse(text_stripped)
            if hindi_check["has_hindi_abuse"]:
                for word in hindi_check["matched_words"]:
                    results["banned_keywords"].append(word)
                    if "hindi_abuse" not in results["keyword_categories"]:
                        results["keyword_categories"].append("hindi_abuse")
                    results["violations"].append(f"hindi_abuse:{word}")
                results["hindi_detection"] = hindi_check
        except Exception as e:
            logger.error(f"Error in Hindi abuse detection: {e}")
        
        # ── Score calculation with context awareness ──
        unique_violations = len(set(results["violations"]))
        
        # Calculate contextual adjustment (reduce score for contextually-safe violations)
        contextual_adjustment = 0.0
        for keyword, context in results.get("context_analysis", {}).items():
            if not context.get('is_harmful', True):
                # Safe usage detected - reduce severity
                contextual_adjustment += 0.15
        
        # More nuanced scoring - not every violation should block
        if unique_violations == 0:
            results["rule_score"] = 0.0
        elif unique_violations == 1:
            # Check what kind of violation it is
            if any(cat in ["violence", "harm", "sexual"] for cat in results["keyword_categories"]):
                results["rule_score"] = 0.5  # Serious violations get medium score
            elif "hindi_abuse" in results["keyword_categories"]:
                results["rule_score"] = 0.4  # Hindi abuse is serious but maybe not always
            elif "spam" in results["violations"]:
                # Spam alone shouldn't block, just reduce score
                results["rule_score"] = 0.1
            else:
                results["rule_score"] = 0.2  # Minor violations (promotional) get low score
        elif unique_violations == 2:
            if any(cat in ["violence", "harm", "sexual"] for cat in results["keyword_categories"]):
                results["rule_score"] = 0.7
            elif "spam" in results["violations"]:
                results["rule_score"] = 0.3
            else:
                results["rule_score"] = 0.4
        else:
            results["rule_score"] = 0.8  # Multiple violations
        
        # Apply contextual adjustment (reduce score for safe usage)
        results["rule_score"] = max(0, results["rule_score"] - contextual_adjustment)
        
        # Apply severity multiplier for dangerous categories
        severity_multiplier = 1.0
        if "violence" in results["keyword_categories"]:
            severity_multiplier = 1.2
        if "harm" in results["keyword_categories"]:
            severity_multiplier = 1.2
        if "sexual" in results["keyword_categories"]:
            severity_multiplier = 1.1
        if "hindi_abuse" in results["keyword_categories"]:
            severity_multiplier = 1.1
        
        results["rule_score"] = min(results["rule_score"] * severity_multiplier, 1.0)
        
        # Log for debugging
        if results["rule_score"] > 0:
            logger.info(f"📊 Rule score: {results['rule_score']:.2f} (violations={unique_violations}, categories={results['keyword_categories']})")
            if results.get("context_analysis"):
                logger.info(f"   Context: {results['context_analysis']}")
        
        return results


# Global instance
rule_engine = RuleEngine()