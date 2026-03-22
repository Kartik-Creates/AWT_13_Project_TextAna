"""
IntentEntityFilter — spaCy NER + regex intent detection pipeline.

Uses spaCy for entity extraction and custom tech entity patterns,
then scores posts using a tiered pattern library with severity weights.
Optionally runs zero-shot classification for ambiguous cases.

Memory: ~50MB (spaCy sm) or ~750MB (spaCy lg). Patterns use ~0MB.
Latency: <5ms patterns-only, 15-30ms with spaCy, 60-80ms with zero-shot.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Pattern library ───────────────────────────────────────────────────────────
# Each entry: (pattern_string, intent_category, severity: 1=low 2=medium 3=high)

INTENT_PATTERNS: List[Tuple[str, str, int]] = [

    # ── Severity 3: High — direct harm instruction ─────────────────────────
    (r'\b(?:steal|stealing|harvest(?:ing)?|exfiltrat(?:e|ing))\s+(?:password|credential|token|cookie|wallet|crypto|key|data)', "credential_theft", 3),
    (r'\b(?:reverse\s+shell|bind\s+shell|web\s+shell|meterpreter|metasploit)', "exploitation", 3),
    (r'\b(?:remote\s+code\s+execution|rce|command\s+injection|os\s+command)', "exploitation", 3),
    (r'\b(?:privilege\s+escalation|privesc|lpe|local\s+priv)', "exploitation", 3),
    (r'\b(?:malware|ransomware|keylogger|rootkit|backdoor|spyware|trojan)\s+(?:creat|build|writ|develop|deploy|spread|install)', "malware_creation", 3),
    (r'\b(?:phishing|spear.?phishing)\s+(?:kit|page|template|campaign)', "phishing", 3),
    (r'\b(?:botnet|ddos)\s+(?:build|creat|run|launch|script|tool)', "attack_infrastructure", 3),
    (r'\b(?:capture|intercept|sniff)\s+(?:credential|password|traffic)\s+.{0,20}(?:user|victim|target)', "surveillance", 3),
    (r'\b(?:extension|plugin|addon|app)\s+.{0,40}(?:steal|harvest|capture)\s+.{0,20}(?:password|credential|key|data)', "malicious_software", 3),

    # ── Severity 2: Medium — likely harmful depending on context ──────────
    (r'\b(?:bypass|circumvent|evade)\s+(?:auth|authentication|2fa|mfa|otp|captcha|rate.?limit|waf|ids|ips)', "bypass_auth", 2),
    (r'\b(?:exploit|exploiting)\s+(?:vulnerable|vulnerability|vuln|unpatched|misconfigured)', "exploitation", 2),
    (r'\bsql\s+injection\b.{0,80}\b(?:login|bypass|admin|dump|extract)', "injection_attack", 2),
    (r'\b(?:xss|cross.site\s+scripting)\b.{0,60}\b(?:steal|hijack|bypass|execute)', "injection_attack", 2),
    (r'\b(?:crack|cracking|brute.?force)\s+(?:password|hash|login|account)', "credential_attack", 2),
    (r'\b(?:jwt|session|cookie|token)\s+(?:forgery|forging|tamper|hijack|bypass)', "session_attack", 2),
    (r'\b(?:monitor|spy|track)\s+.{0,30}(?:without|covert|hidden|stealth|secretly)', "surveillance", 2),
    (r'\b(?:scrape|scrapin)\b.{0,40}\b(?:without\s+permission|unauthorized|violat)', "unauthorized_access", 2),

    # ── Severity 1: Low — suspicious framing but could be legitimate ───────
    (r'\b(?:learn|tutorial|guide|how\s+to|build)\b.{0,60}\b(?:steal|hack|exploit|bypass|crack)', "suspicious_tutorial", 1),
    (r'\b(?:simple|easy|quick|beginner)\b.{0,40}\b(?:hack|exploit|crack|bypass|phish)', "suspicious_tutorial", 1),
    (r'\b(?:teach|show)\s+you\s+how\s+to\b.{0,80}\b(?:hack|exploit|bypass|steal)', "suspicious_tutorial", 1),
    (r'\b(?:anonymou|untrace|undetect)\b', "evasion", 1),
    (r'\b(?:target|victim)\b.{0,30}\b(?:machine|system|server|device|account)', "target_framing", 1),
    (r'\b(?:without\s+(?:detection|being\s+caught|leaving\s+traces))', "evasion", 1),
]

# ── Security research allowlist ───────────────────────────────────────────────
RESEARCH_ALLOWLIST: List[str] = [
    r'\b(?:how\s+to\s+(?:prevent|protect|defend|patch|fix|mitigate|detect|avoid))',
    r'\b(?:security\s+(?:best\s+practices|hardening|audit|research|awareness|posture))',
    r'\b(?:authorized|responsible\s+disclosure|bug\s+bounty|coordinated)',
    r'\bcve-\d{4}-\d+\b',
    r'\bctf\b|\bcapture\s+the\s+flag\b',
    r'\b(?:penetration\s+testing|pentest)\b.{0,80}\b(?:authorized|permission|scope|legal)',
    r'\bdefensive\s+(?:programming|security|coding|measure)',
    r'\b(?:owasp|nist|sans|mitre\s+att&ck)',
    r'\b(?:secure\s+coding|input\s+validation|output\s+encoding|sanitiz)',
    r'\b(?:security\s+research|academic|university|thesis|paper)',
    r'\b(?:demo|proof\s+of\s+concept)\b.{0,40}\b(?:report|disclose|fix|patch)',
]

# ── Custom tech entity patterns for spaCy ruler ───────────────────────────────
TECH_ENTITY_PATTERNS = [
    # Languages
    {"label": "TECH_LANG",  "pattern": [{"LOWER": {"IN": ["python", "javascript", "typescript", "rust", "golang", "java", "kotlin", "swift", "php", "ruby"]}}]},
    # Frameworks
    {"label": "TECH_FW",    "pattern": [{"LOWER": {"IN": ["react", "vue", "angular", "django", "flask", "fastapi", "express", "spring", "rails", "laravel"]}}]},
    # Security tools / concepts
    {"label": "SEC_TOOL",   "pattern": [{"LOWER": {"IN": ["metasploit", "burpsuite", "nmap", "wireshark", "sqlmap", "hydra", "hashcat", "john", "aircrack"]}}]},
    {"label": "SEC_CONCEPT", "pattern": [{"LOWER": {"IN": ["xss", "sqli", "rce", "lfi", "ssrf", "xxe", "idor", "csrf", "ssti"]}}]},
    # Cloud / infra
    {"label": "CLOUD",      "pattern": [{"LOWER": {"IN": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible"]}}]},
    # Attack targets
    {"label": "ATTACK_TARGET", "pattern": [{"LOWER": {"IN": ["api", "server", "database", "credentials", "password", "token", "session", "cookie", "wallet"]}}]},
]


class IntentEntityFilter:
    """Detect harmful intent using NER entity context + tiered pattern matching.

    Optionally uses spaCy for entity extraction to understand what tech
    entities are present and whether they appear in harmful context.

    Args:
        use_spacy:           Whether to use spaCy NER (default True if installed).
        spacy_model:         spaCy model to load (default en_core_web_sm).
        severity_threshold:  Minimum weighted severity score to flag (default 1.5).
        use_ml_confirmation: Whether to use zero-shot for ambiguous cases (default False).
        ml_threshold:        Zero-shot confidence threshold (default 0.70).
    """

    def __init__(
        self,
        use_spacy: bool = True,
        spacy_model: str = "en_core_web_sm",
        severity_threshold: float = 1.5,
        use_ml_confirmation: bool = False,
        ml_threshold: float = 0.70,
    ) -> None:
        self.severity_threshold  = severity_threshold
        self.use_ml_confirmation = use_ml_confirmation
        self.ml_threshold        = ml_threshold
        self._nlp                = None
        self._zs_pipeline        = None

        # Compile patterns
        self._patterns: List[Tuple[re.Pattern, str, int]] = [
            (re.compile(p, re.IGNORECASE | re.DOTALL), cat, sev)
            for p, cat, sev in INTENT_PATTERNS
        ]

        self._allowlist: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE | re.DOTALL)
            for p in RESEARCH_ALLOWLIST
        ]

        # Try loading spaCy
        if use_spacy:
            self._nlp = self._load_spacy(spacy_model)

        logger.info(
            f"IntentEntityFilter initialized: "
            f"spacy={self._nlp is not None}, "
            f"patterns={len(self._patterns)}, "
            f"severity_threshold={severity_threshold}"
        )

    def _load_spacy(self, model_name: str):
        """Load spaCy model with custom entity ruler."""
        try:
            import spacy
            nlp = spacy.load(model_name, disable=["lemmatizer", "textcat"])

            # Add custom entity ruler for tech terms
            if "entity_ruler" not in nlp.pipe_names:
                ruler = nlp.add_pipe("entity_ruler", before="ner")
                ruler.add_patterns(TECH_ENTITY_PATTERNS)

            logger.info(f"✅ spaCy model loaded: {model_name}")
            return nlp
        except OSError:
            logger.warning(
                f"⚠️ spaCy model '{model_name}' not found. "
                f"Run: python -m spacy download {model_name}"
            )
            return None
        except ImportError:
            logger.warning("⚠️ spaCy not installed. Running without NER.")
            return None

    def _load_zs_pipeline(self):
        """Lazy-load zero-shot pipeline."""
        if self._zs_pipeline is None:
            try:
                from transformers import pipeline as hf_pipeline
                self._zs_pipeline = hf_pipeline(
                    "zero-shot-classification",
                    model="cross-encoder/nli-deberta-v3-small",
                    device=-1,
                )
                logger.info("✅ Zero-shot pipeline loaded")
            except Exception as e:
                logger.warning(f"⚠️ Zero-shot pipeline unavailable: {e}")
        return self._zs_pipeline

    def _check_allowlist(self, text: str) -> bool:
        return any(p.search(text) for p in self._allowlist)

    def _run_patterns(self, text: str) -> Dict[str, Any]:
        """Run tiered pattern matching. Returns weighted severity score."""
        category_hits: Dict[str, List[int]] = {}
        matched: List[Dict[str, Any]] = []

        for pattern, category, severity in self._patterns:
            if pattern.search(text):
                category_hits.setdefault(category, []).append(severity)
                matched.append({
                    "pattern":  pattern.pattern[:80],
                    "category": category,
                    "severity": severity,
                })

        if not category_hits:
            return {
                "pattern_score": 0.0,
                "top_category":  None,
                "matched":       [],
                "category_breakdown": {},
            }

        # Weighted score: sum(severity) / total_patterns_checked * scaling
        total_severity = sum(max(sevs) for sevs in category_hits.values())

        # Normalize: score of 3 = max single match, 6+ = definitely harmful
        pattern_score = min(total_severity / 3.0, 1.0)

        # Top category by max severity
        top_category = max(category_hits, key=lambda c: max(category_hits[c]))

        return {
            "pattern_score":    round(pattern_score, 4),
            "top_category":     top_category,
            "matched":          matched,
            "category_breakdown": {
                cat: {"count": len(sevs), "max_severity": max(sevs)}
                for cat, sevs in category_hits.items()
            },
        }

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities using spaCy."""
        if self._nlp is None:
            return {}

        try:
            doc = self._nlp(text[:500])  # limit for speed
            entities: Dict[str, List[str]] = {}
            for ent in doc.ents:
                entities.setdefault(ent.label_, []).append(ent.text)
            return entities
        except Exception as e:
            logger.error(f"spaCy NER failed: {e}")
            return {}

    def _entity_context_score(
        self,
        entities: Dict[str, List[str]],
        pattern_result: Dict[str, Any],
    ) -> float:
        """Boost pattern score when harmful intent targets specific tech entities.

        Logic: harmful intent + specific attack target entity = higher confidence.
        E.g., pattern matches "bypass auth" AND spaCy found "JWT" entity → boost.
        """
        if not pattern_result["top_category"]:
            return 0.0

        boost = 0.0
        attack_targets = entities.get("ATTACK_TARGET", [])
        sec_concepts   = entities.get("SEC_CONCEPT", [])
        sec_tools      = entities.get("SEC_TOOL", [])

        # If harmful category found AND specific attack targets present → boost
        harmful_cats = {"credential_theft", "exploitation", "bypass_auth",
                        "injection_attack", "session_attack", "malware_creation"}

        if pattern_result["top_category"] in harmful_cats:
            if attack_targets:
                boost += 0.10 * min(len(attack_targets), 3)
            if sec_concepts:
                boost += 0.15 * min(len(sec_concepts), 2)
            if sec_tools:
                boost += 0.10 * min(len(sec_tools), 2)

        return round(min(boost, 0.30), 4)

    def _run_zero_shot(self, text: str, hint_category: str) -> Dict[str, Any]:
        """Run zero-shot classification for ambiguous cases."""
        pipe = self._load_zs_pipeline()
        if pipe is None:
            return {"zs_score": 0.0, "zs_available": False}

        labels = [
            "harmful hacking or exploitation tutorial",
            "legitimate security education or research",
            "malicious software creation guide",
            "legitimate programming tutorial",
        ]

        harmful_labels = {
            "harmful hacking or exploitation tutorial",
            "malicious software creation guide",
        }

        try:
            result    = pipe(text[:400], candidate_labels=labels)
            top_label = result["labels"][0]
            top_score = result["scores"][0]
            is_harmful_label = top_label in harmful_labels

            return {
                "zs_available":   True,
                "zs_top_label":   top_label,
                "zs_score":       top_score,
                "zs_is_harmful":  is_harmful_label,
            }
        except Exception as e:
            logger.error(f"Zero-shot failed: {e}")
            return {"zs_score": 0.0, "zs_available": False}

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze a post for harmful tech-context intent.

        Returns:
            is_harmful        : bool
            category          : str
            confidence        : float (0-1)
            pattern_score     : float
            entity_boost      : float
            entities_found    : dict
            matched_patterns  : list
            processing_time_ms: int
        """
        if not text or not text.strip():
            return self._safe_result()

        start = time.time()

        # Allowlist check
        if self._check_allowlist(text):
            return {
                **self._safe_result(),
                "processing_time_ms": round((time.time() - start) * 1000),
                "note": "security_research_allowlist",
            }

        # Pattern matching
        pattern_result = self._run_patterns(text)

        if not pattern_result["top_category"]:
            return {
                **self._safe_result(),
                "processing_time_ms": round((time.time() - start) * 1000),
            }

        # Entity extraction (if spaCy available)
        entities    = self._extract_entities(text)
        entity_boost = self._entity_context_score(entities, pattern_result)

        # Base confidence from pattern score + entity boost
        base_confidence = pattern_result["pattern_score"] + entity_boost
        final_category  = pattern_result["top_category"]
        ml_used         = False

        # Zero-shot for ambiguous cases (pattern_score in gray zone)
        if (self.use_ml_confirmation
                and 0.3 <= base_confidence <= 0.7):
            zs = self._run_zero_shot(text, final_category)
            ml_used = True
            if zs["zs_available"]:
                if zs["zs_is_harmful"] and zs["zs_score"] > self.ml_threshold:
                    base_confidence = min(base_confidence + 0.20, 1.0)
                elif not zs["zs_is_harmful"] and zs["zs_score"] > self.ml_threshold:
                    base_confidence = max(base_confidence - 0.20, 0.0)

        final_confidence = round(min(base_confidence, 1.0), 4)
        is_harmful       = final_confidence >= (self.severity_threshold / 3.0)

        elapsed = round((time.time() - start) * 1000)

        result = {
            "is_harmful":          is_harmful,
            "category":            final_category,
            "confidence":          final_confidence,
            "pattern_score":       pattern_result["pattern_score"],
            "entity_boost":        entity_boost,
            "entities_found":      entities,
            "matched_patterns":    [m["pattern"] for m in pattern_result["matched"]],
            "category_breakdown":  pattern_result["category_breakdown"],
            "ml_used":             ml_used,
            "processing_time_ms":  elapsed,
        }

        if is_harmful:
            logger.warning(
                f"🚨 IntentEntityFilter: harmful intent detected "
                f"category={final_category} confidence={final_confidence:.3f} "
                f"time={elapsed}ms"
            )

        return result

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        return [self.analyze(t) for t in texts]

    def _safe_result(self) -> Dict[str, Any]:
        return {
            "is_harmful":         False,
            "category":           "legitimate_tech",
            "confidence":         0.0,
            "pattern_score":      0.0,
            "entity_boost":       0.0,
            "entities_found":     {},
            "matched_patterns":   [],
            "category_breakdown": {},
            "ml_used":            False,
            "processing_time_ms": 0,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_intent_entity_filter: Optional[IntentEntityFilter] = None


def get_intent_entity_filter() -> IntentEntityFilter:
    global _intent_entity_filter
    if _intent_entity_filter is None:
        use_spacy = os.getenv("INTENT_FILTER_USE_SPACY", "true").lower() == "true"
        threshold = float(os.getenv("INTENT_FILTER_THRESHOLD", "1.5"))
        _intent_entity_filter = IntentEntityFilter(
            use_spacy=use_spacy,
            severity_threshold=threshold,
        )
    return _intent_entity_filter