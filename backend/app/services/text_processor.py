import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import logging
 
logger = logging.getLogger(__name__)
 
class TextProcessor:
    """Processes and extracts information from text.
 
    Provides utilities for URL extraction, mention/hashtag parsing,
    text statistics, and tech signal extraction used by the pipeline.
    """
 
    def __init__(self):
        # URL pattern
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
 
        # Email pattern
        self.email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
 
        # Phone pattern (simplified)
        self.phone_pattern = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
 
        # Mention pattern
        self.mention_pattern = re.compile(r'@(\w+)')
 
        # Hashtag pattern
        self.hashtag_pattern = re.compile(r'#(\w+)')
 
        # ── Tech signal patterns for quick extraction ──
 
        # Version numbers: v1.2.3 or 1.2.3
        self.version_pattern = re.compile(r'\bv?\d+\.\d+(?:\.\d+)?\b')
 
        # Code blocks
        self.code_block_pattern = re.compile(r'```[\w]*\n[\s\S]*?```', re.MULTILINE)
 
        # Inline code
        self.inline_code_pattern = re.compile(r'`[^`]+`')
 
        # HTTP methods (REST API references)
        self.http_method_pattern = re.compile(
            r'\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+/', re.IGNORECASE
        )
 
        # Terminal/shell commands
        self.shell_command_pattern = re.compile(
            r'(?:^|\s)\$\s+\w+', re.MULTILINE
        )
 
        # Package manager commands
        self.pkg_command_pattern = re.compile(
            r'\b(?:npm|yarn|pnpm|pip|cargo|go|brew|apt|conda)\s+'
            r'(?:install|add|remove|run|build|test|publish|init)\b',
            re.IGNORECASE
        )
 
        # Git commands
        self.git_command_pattern = re.compile(
            r'\bgit\s+(?:clone|push|pull|commit|merge|rebase|checkout|branch|stash|log|diff|status)\b',
            re.IGNORECASE
        )
 
        # Docker commands
        self.docker_command_pattern = re.compile(
            r'\bdocker(?:-compose)?\s+(?:run|build|push|pull|up|down|exec|logs|ps|stop)\b',
            re.IGNORECASE
        )
 
        # Import statements (Python / JS / TS)
        self.import_pattern = re.compile(
            r'\b(?:import|from|require|use)\s+[\w\.\{\}\'\"]+',
            re.IGNORECASE
        )
 
        # Function / class definitions
        self.definition_pattern = re.compile(
            r'\b(?:def|class|function|const|let|var|async\s+function|fn|func)\s+\w+',
            re.IGNORECASE
        )
 
        # Big O notation
        self.bigo_pattern = re.compile(r'O\((?:n|log\s*n|n\s*log\s*n|n[²2]|1|k)\)', re.IGNORECASE)
 
        # Tech hashtags (common ones)
        self.tech_hashtag_pattern = re.compile(
            r'#(?:python|javascript|typescript|react|vue|angular|nextjs|django|fastapi|'
            r'golang|rust|java|kotlin|swift|docker|kubernetes|aws|gcp|azure|'
            r'machinelearning|deeplearning|ai|llm|rag|devops|sre|opensource|'
            r'programming|coding|developer|softwareengineering|webdev|'
            r'100daysofcode|buildinpublic|techtwitter|leetcode|hackathon)\b',
            re.IGNORECASE
        )
 
        # Tech domain URLs
        self.tech_domain_pattern = re.compile(
            r'https?://(?:www\.)?(?:github|gitlab|stackoverflow|npmjs|pypi|'
            r'docs\.\w+|developer\.\w+|hackernews|leetcode|kaggle|'
            r'huggingface|arxiv|dev\.to|hashnode|codepen|replit)\.(?:com|org|io|co)',
            re.IGNORECASE
        )
 
    # ──────────────────────────────────────────────────────────
    #  Existing methods
    # ──────────────────────────────────────────────────────────
 
    def extract_urls(self, text: str) -> List[Dict[str, Any]]:
        """Extract and analyze URLs from text."""
        if not text:
            return []
 
        urls = []
        matches = self.url_pattern.finditer(text)
 
        for match in matches:
            url = match.group()
            try:
                parsed = urlparse(url)
                urls.append({
                    "full_url": url,
                    "domain": parsed.netloc,
                    "path": parsed.path,
                    "params": parsed.params,
                    "query": parsed.query,
                    "fragment": parsed.fragment,
                    "is_shortened": self._is_shortened_url(parsed.netloc),
                    "is_tech_domain": self._is_tech_domain(parsed.netloc),
                })
            except Exception:
                urls.append({
                    "full_url": url,
                    "domain": "unknown",
                    "is_shortened": False,
                    "is_tech_domain": False,
                })
 
        return urls
 
    def _is_shortened_url(self, domain: str) -> bool:
        """Check if URL is from a known URL shortener."""
        shorteners = {
            'bit.ly', 'tinyurl.com', 'goo.gl', 'ow.ly',
            'short.link', 'rb.gy', 'cutt.ly', 'is.gd',
            't.co', 'buff.ly', 'tiny.cc', 'tr.im'
        }
        return domain.lower() in shorteners
 
    def _is_tech_domain(self, domain: str) -> bool:
        """Check if domain belongs to a known tech resource."""
        tech_domains = {
            'github.com', 'gitlab.com', 'bitbucket.org',
            'stackoverflow.com', 'stackexchange.com',
            'npmjs.com', 'pypi.org', 'crates.io',
            'hub.docker.com', 'dev.to', 'hashnode.com',
            'leetcode.com', 'hackerrank.com', 'codeforces.com',
            'codepen.io', 'replit.com', 'codesandbox.io',
            'vercel.com', 'netlify.com', 'arxiv.org',
            'huggingface.co', 'kaggle.com', 'producthunt.com',
        }
        domain_lower = domain.lower().lstrip('www.')
        return domain_lower in tech_domains
 
    def extract_mentions(self, text: str) -> List[str]:
        """Extract @mentions from text."""
        if not text:
            return []
        return self.mention_pattern.findall(text)
 
    def extract_hashtags(self, text: str) -> List[str]:
        """Extract #hashtags from text."""
        if not text:
            return []
        return self.hashtag_pattern.findall(text)
 
    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses."""
        if not text:
            return []
        return self.email_pattern.findall(text)
 
    def extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers."""
        if not text:
            return []
        return self.phone_pattern.findall(text)
 
    def get_text_stats(self, text: str) -> Dict[str, Any]:
        """Get basic text statistics."""
        if not text:
            return {
                "char_count": 0,
                "word_count": 0,
                "sentence_count": 0,
                "avg_word_length": 0,
                "has_uppercase": False,
                "has_numbers": False,
                "has_special_chars": False
            }
 
        words = text.split()
 
        return {
            "char_count": len(text),
            "word_count": len(words),
            "sentence_count": len(re.split(r'[.!?]+', text)) - 1,
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
            "has_uppercase": any(c.isupper() for c in text),
            "has_numbers": any(c.isdigit() for c in text),
            "has_special_chars": any(not c.isalnum() and not c.isspace() for c in text)
        }
 
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        text = ' '.join(text.split())
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        return text.strip()
 
    # ──────────────────────────────────────────────────────────
    #  New: Tech signal extraction
    # ──────────────────────────────────────────────────────────
 
    def extract_tech_signals(self, text: str) -> Dict[str, Any]:
        """Extract all concrete tech signals from a post.
 
        Returns a structured dict of signals with counts and examples,
        useful for debugging and for feeding into the decision pipeline.
        """
        if not text:
            return self._empty_tech_signals()
 
        signals: Dict[str, Any] = {}
 
        # Code blocks (strong signal)
        code_blocks = self.code_block_pattern.findall(text)
        signals["code_blocks"] = len(code_blocks)
 
        # Inline code
        inline_code = self.inline_code_pattern.findall(text)
        signals["inline_code"] = len(inline_code)
 
        # Version numbers
        versions = self.version_pattern.findall(text)
        signals["version_numbers"] = versions[:5]  # cap for logging
 
        # HTTP methods
        http_methods = self.http_method_pattern.findall(text)
        signals["http_methods"] = http_methods
 
        # Shell commands
        shell_cmds = self.shell_command_pattern.findall(text)
        signals["shell_commands"] = len(shell_cmds)
 
        # Package manager commands
        pkg_cmds = self.pkg_command_pattern.findall(text)
        signals["package_commands"] = pkg_cmds
 
        # Git commands
        git_cmds = self.git_command_pattern.findall(text)
        signals["git_commands"] = git_cmds
 
        # Docker commands
        docker_cmds = self.docker_command_pattern.findall(text)
        signals["docker_commands"] = docker_cmds
 
        # Import statements
        imports = self.import_pattern.findall(text)
        signals["imports"] = len(imports)
 
        # Function / class definitions
        definitions = self.definition_pattern.findall(text)
        signals["definitions"] = len(definitions)
 
        # Big O notation
        bigo = self.bigo_pattern.findall(text)
        signals["big_o_notation"] = bigo
 
        # Tech hashtags
        tech_hashtags = self.tech_hashtag_pattern.findall(text)
        signals["tech_hashtags"] = tech_hashtags
 
        # Tech domain URLs
        tech_urls = self.tech_domain_pattern.findall(text)
        signals["tech_urls"] = len(tech_urls)
 
        # Aggregate signal strength (0–1)
        signals["signal_strength"] = self.calculate_tech_signal_strength(signals)
 
        return signals
 
    def calculate_tech_signal_strength(self, signals: Dict[str, Any]) -> float:
        """Convert extracted tech signals into a 0–1 strength score.
 
        Each signal type contributes a weighted amount, capped at 1.0.
        This score is meant to be combined with the taxonomy-based score
        in RuleEngine.check_tech_relevance(), not used standalone.
        """
        score = 0.0
 
        # Strong signals (code is always tech)
        if signals.get("code_blocks", 0) > 0:
            score += 0.40
        if signals.get("inline_code", 0) > 0:
            score += 0.20
 
        # Medium signals
        if signals.get("imports", 0) > 0:
            score += 0.15
        if signals.get("definitions", 0) > 0:
            score += 0.15
        if signals.get("tech_urls", 0) > 0:
            score += 0.20
 
        # Lighter signals
        if signals.get("version_numbers"):
            score += 0.10
        if signals.get("http_methods"):
            score += 0.10
        if signals.get("package_commands"):
            score += 0.15
        if signals.get("git_commands"):
            score += 0.10
        if signals.get("docker_commands"):
            score += 0.10
        if signals.get("tech_hashtags"):
            score += min(len(signals["tech_hashtags"]) * 0.05, 0.15)
        if signals.get("big_o_notation"):
            score += 0.10
        if signals.get("shell_commands", 0) > 0:
            score += 0.10
 
        return round(min(score, 1.0), 3)
 
    def calculate_tech_density(self, text: str, tech_terms: List[str]) -> float:
        """Calculate the density of tech terms in the text (0–1).
 
        Density = (number of matched tech terms) / (total word count) * scaling.
        Returns 0.0 if text is empty or no terms matched.
 
        Args:
            text: The raw post text.
            tech_terms: List of matched tech terms (from RuleEngine.check_tech_relevance).
        """
        if not text or not tech_terms:
            return 0.0
 
        total_words = max(len(text.split()), 1)
        unique_terms = len(set(tech_terms))
 
        # Raw density (terms per word)
        raw_density = unique_terms / total_words
 
        # Scale to 0–1 using a soft cap:
        # 0.10 (1 term per 10 words) maps to ~1.0 density
        scaled = min(raw_density / 0.10, 1.0)
 
        return round(scaled, 3)
 
    def _empty_tech_signals(self) -> Dict[str, Any]:
        """Return empty tech signals structure."""
        return {
            "code_blocks": 0,
            "inline_code": 0,
            "version_numbers": [],
            "http_methods": [],
            "shell_commands": 0,
            "package_commands": [],
            "git_commands": [],
            "docker_commands": [],
            "imports": 0,
            "definitions": 0,
            "big_o_notation": [],
            "tech_hashtags": [],
            "tech_urls": 0,
            "signal_strength": 0.0,
        }
 