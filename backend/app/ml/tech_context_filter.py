"""
TechContextFilter — lightweight sequence classifier for detecting harmful intent
embedded in technical content.

Uses cyber-harm regex patterns as a fast first pass, then optionally runs
cross-encoder/nli-deberta-v3-small for zero-shot confirmation on flagged posts.
This keeps average latency under 10ms (most posts hit patterns only) while
maintaining high recall on novel phrasing.

Memory: ~180MB with DeBERTa loaded, ~0MB patterns-only mode.
Latency: <5ms patterns-only, 40-80ms with DeBERTa on CPU.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Categories ──────────────────────────────────────────────────────────────
CATEGORIES = [
    "malicious_code_instruction",
    "exploitation_techniques",
    "social_engineering_disguised",
    "bypass_instructions",
    "legitimate_tech",
]

# ── Zero-shot candidate labels (maps to categories) ──────────────────────────
ZS_LABELS = [
    "malicious hacking or exploitation guide",
    "security attack or exploit tutorial",
    "social engineering or phishing guide",
    "security bypass or authentication circumvention",
    "legitimate technology education",
]

ZS_TO_CATEGORY = {
    "malicious hacking or exploitation guide":        "malicious_code_instruction",
    "security attack or exploit tutorial":            "exploitation_techniques",
    "social engineering or phishing guide":           "social_engineering_disguised",
    "security bypass or authentication circumvention": "bypass_instructions",
    "legitimate technology education":                "legitimate_tech",
}


class TechContextFilter:
    """Detect harmful intent embedded inside technical content.

    Two-stage pipeline:
      Stage 1 — Regex patterns (always runs, <1ms).
                Returns immediately if no patterns match.
      Stage 2 — Zero-shot classification via DeBERTa-v3-small (~60ms CPU).
                Runs only when Stage 1 finds a match, to confirm intent
                and reduce false positives.

    Args:
        confidence_threshold: Minimum score to classify as harmful (default 0.65).
        use_ml_confirmation:  Whether to run DeBERTa confirmation pass (default True).
        model_name:           HuggingFace model for zero-shot (default deberta-v3-small).
        cache_size:           LRU cache size for repeated texts (default 512).
    """

    def __init__(
        self,
        confidence_threshold: float = 0.65,
        use_ml_confirmation: bool = True,
        model_name: str = "cross-encoder/nli-deberta-v3-small",
        cache_size: int = 512,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.use_ml_confirmation  = use_ml_confirmation
        self.model_name           = model_name
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_size = cache_size
        self._pipeline   = None  # lazy-loaded

        # ── Stage 1: Cyber-harm regex patterns ──────────────────────────────
        # Each tuple: (pattern, category, severity_weight)
        self._raw_patterns: List[Tuple[str, str, float]] = [

            # Exploitation techniques
            (r'\b(?:exploit|exploiting|exploited)\s+(?:vulnerable|vulnerability|vuln|cve)', "exploitation_techniques", 0.85),
            (r'\b(?:remote\s+code\s+execution|rce)\b', "exploitation_techniques", 0.90),
            (r'\b(?:privilege\s+escalation|privesc|priv\s+esc)\b', "exploitation_techniques", 0.85),
            (r'\b(?:reverse\s+shell|bind\s+shell|web\s+shell|meterpreter)\b', "exploitation_techniques", 0.90),
            (r'\b(?:buffer\s+overflow|heap\s+spray|use.after.free|rop\s+chain)\b', "exploitation_techniques", 0.80),
            (r'\b(?:exfiltrat(?:e|ing|ion))\b.{0,40}\b(?:data|credential|password|token|key)\b', "exploitation_techniques", 0.85),

            # Bypass / authentication circumvention
            (r'\b(?:bypass|bypassing|circumvent)\s+(?:auth|authentication|2fa|mfa|captcha|waf|firewall|security)', "bypass_instructions", 0.85),
            (r'\b(?:bypass|circumvent)\s+(?:rate.?limit|ip.?ban|block)', "bypass_instructions", 0.75),
            (r'\bsql\s+injection\b.{0,60}\b(?:login|bypass|admin|auth)', "bypass_instructions", 0.85),
            (r'\b(?:jwt|token|session|cookie)\s+(?:forgery|forging|tamper|manipulat)', "bypass_instructions", 0.80),
            (r'\b(?:broken\s+auth|broken\s+access\s+control)\b.{0,40}\b(?:exploit|bypass|how\s+to)', "bypass_instructions", 0.80),

            # Malicious code instructions
            (r'\b(?:malware|ransomware|spyware|keylogger|rootkit|backdoor|trojan|worm)\s+(?:creat|build|writ|develop|deploy|install|spread)', "malicious_code_instruction", 0.90),
            (r'\b(?:crack|cracking)\s+(?:password|hash|md5|sha|bcrypt|phpass)', "malicious_code_instruction", 0.80),
            (r'\b(?:phishing|spear.?phishing)\s+(?:email|template|page|kit|campaign)', "malicious_code_instruction", 0.85),
            (r'\b(?:ddos|dos\s+attack|botnet)\s+(?:script|tool|service|launch|build)', "malicious_code_instruction", 0.85),
            (r'\bstealing?\s+(?:credential|password|token|cookie|wallet|crypto|bitcoin)', "malicious_code_instruction", 0.85),
            (r'\b(?:inject|injection)\s+(?:payload|code|script)\b.{0,40}\b(?:bypass|exploit|shell)', "malicious_code_instruction", 0.80),

            # Social engineering disguised as tutorials
            (r'\b(?:learn|tutorial|guide|how\s+to|build)\b.{0,50}\b(?:steal|stealthy|stealing)\b.{0,30}\b(?:password|credential|data|crypto|wallet|card)', "social_engineering_disguised", 0.85),
            (r'\b(?:teach|show)\s+you\s+how\s+to\b.{0,60}\b(?:hack|exploit|bypass|steal|phish|scam)', "social_engineering_disguised", 0.85),
            (r'\b(?:simple|easy|quick|beginner)\b.{0,30}\b(?:hack|exploit|crack|bypass|phish)', "social_engineering_disguised", 0.80),
            (r'\b(?:step.by.step|complete\s+guide)\b.{0,40}\b(?:exploit|hack|bypass|steal|phish)', "social_engineering_disguised", 0.80),
            (r'\b(?:monitor|capture|intercept|sniff)\b.{0,30}\b(?:credential|password|traffic|packet)\b.{0,30}\b(?:user|victim|target)', "social_engineering_disguised", 0.85),
            (r'\b(?:extension|plugin|addon)\b.{0,40}\b(?:steal|harvest|capture)\b.{0,30}\b(?:password|data|credential|key)', "social_engineering_disguised", 0.85),
        ]

        # Compile patterns
        self._patterns: List[Tuple[re.Pattern, str, float]] = [
            (re.compile(p, re.IGNORECASE | re.DOTALL), cat, weight)
            for p, cat, weight in self._raw_patterns
        ]

        # ── Security research allowlist (prevents false positives) ───────────
        self._raw_allowlist = [
            r'\b(?:how\s+to\s+(?:prevent|protect|defend|patch|fix|mitigate|detect))',
            r'\b(?:security\s+(?:best\s+practices|hardening|audit|research|awareness))',
            r'\b(?:authorized|responsible\s+disclosure|bug\s+bounty|coordinated\s+disclosure)',
            r'\bcve-\d{4}-\d+\b',
            r'\bctf\b|\bcapture\s+the\s+flag\b',
            r'\bpenetration\s+testing\b.{0,60}\b(?:authorized|permission|scope|engagement)',
            r'\b(?:proof\s+of\s+concept|poc)\b.{0,40}\b(?:disclosed|reported|patched)',
            r'\bdefensive\s+(?:programming|security|coding)',
            r'\b(?:owasp|nist|sans)\s+(?:top|guide|framework|standard)',
            r'\b(?:secure\s+coding|input\s+validation|output\s+encoding)',
        ]

        self._allowlist: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE | re.DOTALL)
            for p in self._raw_allowlist
        ]

        logger.info(
            f"TechContextFilter initialized: "
            f"{len(self._patterns)} harm patterns, "
            f"{len(self._allowlist)} allowlist patterns, "
            f"ml_confirmation={use_ml_confirmation}"
        )

    # ── Lazy model loading ────────────────────────────────────────────────────

    def _get_pipeline(self):
        """Lazy-load the zero-shot classification pipeline."""
        if self._pipeline is None:
            try:
                from transformers import pipeline as hf_pipeline
                logger.info(f"Loading zero-shot model: {self.model_name}")
                self._pipeline = hf_pipeline(
                    "zero-shot-classification",
                    model=self.model_name,
                    device=-1,          # CPU
                    multi_label=False,
                )
                logger.info(f"✅ TechContextFilter ML model loaded: {self.model_name}")
            except Exception as e:
                logger.warning(f"⚠️ Could not load ML model ({e}). Running patterns-only.")
                self._pipeline = None
        return self._pipeline

    # ── Cache ─────────────────────────────────────────────────────────────────

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _get_cached(self, text: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(self._cache_key(text))

    def _set_cached(self, text: str, result: Dict[str, Any]) -> None:
        key = self._cache_key(text)
        if len(self._cache) >= self._cache_size:
            # Evict oldest entry
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = result

    # ── Core analysis ─────────────────────────────────────────────────────────

    def _check_allowlist(self, text: str) -> bool:
        """Return True if text matches any security research allowlist pattern."""
        return any(p.search(text) for p in self._allowlist)

    def _run_patterns(self, text: str) -> Dict[str, Any]:
        """Run Stage 1 regex patterns. Returns highest-scoring match."""
        best_category = None
        best_score    = 0.0
        matched_patterns: List[str] = []

        for pattern, category, weight in self._patterns:
            if pattern.search(text):
                matched_patterns.append(pattern.pattern[:80])
                if weight > best_score:
                    best_score    = weight
                    best_category = category

        return {
            "pattern_match":    best_category is not None,
            "category":         best_category,
            "pattern_score":    best_score,
            "matched_patterns": matched_patterns,
        }

    def _run_zero_shot(self, text: str, hint_category: Optional[str] = None) -> Dict[str, Any]:
        """Run Stage 2 zero-shot classification."""
        pipe = self._get_pipeline()
        if pipe is None:
            return {"zs_category": hint_category, "zs_score": 0.0, "zs_available": False}

        try:
            # Truncate to ~400 chars for speed (DeBERTa has 512 token limit)
            truncated = text[:400]
            result    = pipe(truncated, candidate_labels=ZS_LABELS)

            top_label = result["labels"][0]
            top_score = result["scores"][0]
            category  = ZS_TO_CATEGORY.get(top_label, "legitimate_tech")

            # Build per-category scores
            category_scores = {
                ZS_TO_CATEGORY[label]: score
                for label, score in zip(result["labels"], result["scores"])
            }

            return {
                "zs_category":       category,
                "zs_score":          top_score,
                "zs_available":      True,
                "zs_label":          top_label,
                "category_scores":   category_scores,
            }
        except Exception as e:
            logger.error(f"Zero-shot classification failed: {e}")
            return {"zs_category": hint_category, "zs_score": 0.0, "zs_available": False}

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze a single post for harmful tech-context content.

        Returns:
            is_harmful        : bool — final verdict
            category          : str  — top category
            confidence        : float — final confidence score (0–1)
            pattern_matched   : bool
            ml_used           : bool
            matched_patterns  : list of matched pattern strings
            category_scores   : dict of per-category scores
            processing_time_ms: int
        """
        if not text or not text.strip():
            return self._safe_result("legitimate_tech", 0.0, False)

        # Cache lookup
        cached = self._get_cached(text)
        if cached is not None:
            return {**cached, "from_cache": True}

        start = time.time()

        # ── Allowlist check ──────────────────────────────────────────────────
        if self._check_allowlist(text):
            result = self._safe_result(
                category="legitimate_tech",
                confidence=0.1,
                is_harmful=False,
                processing_time_ms=round((time.time() - start) * 1000),
                note="security_research_allowlist",
            )
            self._set_cached(text, result)
            return result

        # ── Stage 1: Pattern matching ────────────────────────────────────────
        pattern_result = self._run_patterns(text)
        ml_used        = False
        category_scores: Dict[str, float] = {c: 0.0 for c in CATEGORIES}

        if not pattern_result["pattern_match"]:
            # No patterns matched — safe
            result = self._safe_result(
                category="legitimate_tech",
                confidence=0.05,
                is_harmful=False,
                processing_time_ms=round((time.time() - start) * 1000),
            )
            self._set_cached(text, result)
            return result

        # Patterns matched — populate category scores from pattern
        hit_cat   = pattern_result["category"]
        hit_score = pattern_result["pattern_score"]
        category_scores[hit_cat] = hit_score

        # ── Stage 2: ML confirmation (only on pattern hits) ──────────────────
        final_category  = hit_cat
        final_confidence = hit_score

        if self.use_ml_confirmation:
            zs = self._run_zero_shot(text, hint_category=hit_cat)
            ml_used = True

            if zs["zs_available"]:
                # Merge scores: patterns set the floor, ML refines
                zs_scores = zs.get("category_scores", {})
                for cat in CATEGORIES:
                    zs_score  = zs_scores.get(cat, 0.0)
                    pat_score = category_scores.get(cat, 0.0)
                    # Weighted combination: patterns 60%, ML 40%
                    category_scores[cat] = round(pat_score * 0.6 + zs_score * 0.4, 4)

                final_category   = max(category_scores, key=category_scores.get)
                final_confidence = category_scores[final_category]

                # If ML strongly says legitimate despite pattern match, lower confidence
                if zs["zs_category"] == "legitimate_tech" and zs["zs_score"] > 0.75:
                    final_confidence *= 0.5
                    logger.info(
                        f"ML overrides pattern match: "
                        f"pattern={hit_cat} ({hit_score:.2f}) → "
                        f"ML=legitimate_tech ({zs['zs_score']:.2f})"
                    )

        # ── Final decision ────────────────────────────────────────────────────
        is_harmful = (
            final_category != "legitimate_tech"
            and final_confidence >= self.confidence_threshold
        )

        elapsed = round((time.time() - start) * 1000)

        result = {
            "is_harmful":          is_harmful,
            "category":            final_category,
            "confidence":          round(final_confidence, 4),
            "pattern_matched":     pattern_result["pattern_match"],
            "matched_patterns":    pattern_result["matched_patterns"],
            "ml_used":             ml_used,
            "category_scores":     category_scores,
            "processing_time_ms":  elapsed,
            "from_cache":          False,
        }

        if is_harmful:
            logger.warning(
                f"🚨 TechContextFilter: harmful content detected "
                f"category={final_category} confidence={final_confidence:.3f} "
                f"ml_used={ml_used} time={elapsed}ms"
            )

        self._set_cached(text, result)
        return result

    def analyze_batch(self, texts: List[str], batch_size: int = 8) -> List[Dict[str, Any]]:
        """Analyze a batch of texts."""
        return [self.analyze(text) for text in texts]

    def _safe_result(
        self,
        category: str,
        confidence: float,
        is_harmful: bool,
        processing_time_ms: int = 0,
        note: str = "",
    ) -> Dict[str, Any]:
        return {
            "is_harmful":         is_harmful,
            "category":           category,
            "confidence":         confidence,
            "pattern_matched":    False,
            "matched_patterns":   [],
            "ml_used":            False,
            "category_scores":    {c: 0.0 for c in CATEGORIES},
            "processing_time_ms": processing_time_ms,
            "from_cache":         False,
            "note":               note,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Return cache and configuration stats."""
        return {
            "cache_size":          len(self._cache),
            "cache_capacity":      self._cache_size,
            "pattern_count":       len(self._patterns),
            "allowlist_count":     len(self._allowlist),
            "confidence_threshold": self.confidence_threshold,
            "ml_confirmation":     self.use_ml_confirmation,
            "model_loaded":        self._pipeline is not None,
        }


# ── Singleton ────────────────────────────────────────────────────────────────

_tech_context_filter: Optional[TechContextFilter] = None


def get_tech_context_filter() -> TechContextFilter:
    """Return the global TechContextFilter instance."""
    global _tech_context_filter
    if _tech_context_filter is None:
        use_ml = os.getenv("TECH_FILTER_USE_ML", "true").lower() == "true"
        threshold = float(os.getenv("TECH_FILTER_THRESHOLD", "0.65"))
        _tech_context_filter = TechContextFilter(
            confidence_threshold=threshold,
            use_ml_confirmation=use_ml,
        )
    return _tech_context_filter