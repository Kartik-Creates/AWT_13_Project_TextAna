import re
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """Text preprocessing utilities for the moderation pipeline.

    Provides:
      - Text cleaning and normalization
      - URL extraction
      - Tokenization and stopword removal
      - Unicode normalization
      - Tech signal extraction for pre-filtering  (NEW)
      - BERT/CLIP input preparation               (NEW)
    """

    # BERT max tokens (safe character proxy: ~4 chars/token on average)
    _BERT_CHAR_LIMIT = 512
    # CLIP hard limit
    _CLIP_CHAR_LIMIT = 200

    def __init__(self):
        # Stopwords for token filtering
        self._stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because',
            'as', 'what', 'which', 'this', 'that', 'these', 'those',
            'then', 'just', 'so', 'than', 'such', 'both', 'through',
            'about', 'for', 'is', 'of', 'while', 'during', 'to', 'from',
            'in', 'on', 'at', 'by', 'with', 'it', 'its', 'be', 'was',
            'are', 'were', 'been', 'being', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'must', 'can', 'not', 'no', 'up', 'out', 'very',
        }

        # URL pattern
        self._url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )

        # Code block pattern (Markdown)
        self._code_block_pattern = re.compile(r'```[\w]*\n[\s\S]*?```', re.MULTILINE)

        # Inline code pattern
        self._inline_code_pattern = re.compile(r'`[^`]+`')

        # Mention and hashtag patterns
        self._mention_pattern = re.compile(r'@\w+')
        self._hashtag_pattern = re.compile(r'#\w+')

        # Leetspeak normalization map (same as RuleEngine for consistency)
        self._leet_map = {
            '0': 'o', '1': 'i', '2': 'z', '3': 'e', '4': 'a',
            '5': 's', '6': 'b', '7': 't', '8': 'b', '9': 'g',
            '@': 'a', '$': 's', '!': 'i', '+': 't', '|': 'i'
        }

    # ──────────────────────────────────────────────────────────
    #  Core text cleaning
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text for general use.

        - Lowercases
        - Collapses whitespace
        - Removes non-alphanumeric characters except basic punctuation
        """
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.\,\!\?\-\'\"]', '', text)
        return text.strip()

    def clean_for_bert(self, text: str) -> str:
        """Prepare text for BERT-family models.

        - Preserves original casing (BERT is case-sensitive in most variants)
        - Removes Markdown code blocks (BERT doesn't understand code syntax)
        - Collapses whitespace
        - Hard-truncates to BERT's safe character limit
        """
        if not text:
            return ""

        # Strip code blocks — BERT handles prose, not code
        t = self._code_block_pattern.sub(' [CODE] ', text)
        t = self._inline_code_pattern.sub(' [CODE] ', t)

        # Collapse whitespace
        t = re.sub(r'\s+', ' ', t).strip()

        # Hard-truncate for BERT's token limit
        if len(t) > self._BERT_CHAR_LIMIT:
            logger.debug(f"Text truncated from {len(t)} to {self._BERT_CHAR_LIMIT} chars for BERT")
            t = t[:self._BERT_CHAR_LIMIT]

        return t

    def clean_for_clip(self, text: str) -> str:
        """Prepare text for CLIP (image-text similarity).

        CLIP works best with short, natural-language descriptions.
        Strip code, URLs, and mentions — keep the human-readable content.
        """
        if not text:
            return ""

        # Remove URLs
        t = self._url_pattern.sub('', text)
        # Remove code blocks
        t = self._code_block_pattern.sub('', t)
        t = self._inline_code_pattern.sub('', t)
        # Remove mentions and hashtags
        t = self._mention_pattern.sub('', t)
        t = self._hashtag_pattern.sub('', t)
        # Collapse whitespace
        t = re.sub(r'\s+', ' ', t).strip()
        # Truncate to CLIP char limit
        if len(t) > self._CLIP_CHAR_LIMIT:
            t = t[:self._CLIP_CHAR_LIMIT]

        return t

    def normalize_leetspeak(self, text: str) -> str:
        """Replace common leetspeak substitutions for keyword matching."""
        normalized = text.lower()
        for leet, char in self._leet_map.items():
            normalized = normalized.replace(leet, char)
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        return ' '.join(normalized.split())

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract raw URL strings from text."""
        url_pattern = (
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return re.findall(url_pattern, text)

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Simple whitespace tokenization."""
        return text.split()

    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """Remove common English stopwords from a token list."""
        return [t for t in tokens if t.lower() not in self._stopwords]

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Normalize unicode characters to ASCII where possible."""
        try:
            import unicodedata
            return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        except Exception:
            return text

    # ──────────────────────────────────────────────────────────
    #  Tech signal extraction
    # ──────────────────────────────────────────────────────────

    def extract_code_blocks(self, text: str) -> List[str]:
        """Return all Markdown code blocks found in text."""
        return self._code_block_pattern.findall(text)

    def extract_inline_code(self, text: str) -> List[str]:
        """Return all inline code snippets (backtick-wrapped) found in text."""
        return self._inline_code_pattern.findall(text)

    def extract_hashtags(self, text: str) -> List[str]:
        """Return all #hashtag strings found in text."""
        return self._hashtag_pattern.findall(text)

    def extract_mentions(self, text: str) -> List[str]:
        """Return all @mention strings found in text."""
        return self._mention_pattern.findall(text)

    def has_code_content(self, text: str) -> bool:
        """Return True if text contains Markdown code blocks or inline code."""
        return bool(
            self._code_block_pattern.search(text)
            or self._inline_code_pattern.search(text)
        )

    def get_tech_pre_filter(self, text: str) -> Dict[str, Any]:
        """Quick, cheap tech pre-filter before running expensive ML models.

        Used by the pipeline to decide whether it's worth calling the ML stack.
        This does NOT replace RuleEngine.check_tech_relevance() — it is a fast
        preliminary gate only.

        Returns:
            worth_ml_analysis : bool — if False, skip ML and use rule-based decision
            signals           : dict of raw signal counts
            reason            : short explanation string
        """
        if not text or not text.strip():
            return {
                "worth_ml_analysis": False,
                "signals": {},
                "reason": "empty_text",
            }

        signals: Dict[str, Any] = {
            "has_code_blocks": bool(self._code_block_pattern.search(text)),
            "has_inline_code": bool(self._inline_code_pattern.search(text)),
            "code_block_count": len(self._code_block_pattern.findall(text)),
            "inline_code_count": len(self._inline_code_pattern.findall(text)),
            "char_count": len(text),
            "word_count": len(text.split()),
        }

        # Code is unambiguous tech content — always worth ML harm analysis
        if signals["has_code_blocks"] or signals["has_inline_code"]:
            return {
                "worth_ml_analysis": True,
                "signals": signals,
                "reason": "contains_code",
            }

        # Very short posts with no other signals are cheap to analyze
        if signals["word_count"] < 5:
            return {
                "worth_ml_analysis": True,
                "signals": signals,
                "reason": "short_post_analyze_anyway",
            }

        # Default: analyze everything — let RuleEngine and ML decide
        return {
            "worth_ml_analysis": True,
            "signals": signals,
            "reason": "default_analyze",
        }

    def prepare_for_pipeline(self, text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Prepare all pre-processed text variants needed by the pipeline.

        Returns a dict with ready-to-use inputs for each downstream component:
          - raw          : original text (unchanged)
          - for_bert     : cleaned for BERT toxicity model
          - for_clip     : cleaned for CLIP image-text similarity
          - for_rules    : leetspeak-normalized for rule engine keyword matching
          - has_image    : bool
          - image_valid  : bool (only meaningful when has_image=True)
          - pre_filter   : tech pre-filter result
        """
        prepared: Dict[str, Any] = {
            "raw": text,
            "for_bert": self.clean_for_bert(text),
            "for_clip": self.clean_for_clip(text),
            "for_rules": self.normalize_leetspeak(text),
            "has_image": image_path is not None,
            "image_valid": False,
            "pre_filter": self.get_tech_pre_filter(text),
        }

        if image_path:
            prepared["image_valid"] = ImagePreprocessor.validate_image(image_path)

        return prepared


# ──────────────────────────────────────────────────────────────────────────────
#  Image preprocessing
# ──────────────────────────────────────────────────────────────────────────────

class ImagePreprocessor:
    """Image preprocessing utilities."""

    # Supported formats for CLIP / EfficientNet
    SUPPORTED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "GIF", "BMP"}

    @staticmethod
    def validate_image(image_path: str) -> bool:
        """Validate if image exists, is readable, and is in a supported format."""
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception as e:
            logger.warning(f"Image validation failed for {image_path}: {e}")
            return False

    @staticmethod
    def get_image_info(image_path: str) -> Dict[str, Any]:
        """Get basic image metadata."""
        try:
            from PIL import Image
            import os

            with Image.open(image_path) as img:
                return {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height,
                    "file_size_bytes": os.path.getsize(image_path),
                    "is_supported": img.format in ImagePreprocessor.SUPPORTED_FORMATS,
                }
        except Exception as e:
            logger.error(f"Error getting image info for {image_path}: {e}")
            return {}

    @staticmethod
    def resize_for_model(image_path: str, target_size: Tuple[int, int] = (224, 224)) -> Any:
        """Load and resize an image to the target size for model input.

        Returns a PIL Image object, or None on failure.
        """
        try:
            from PIL import Image
            img = Image.open(image_path).convert("RGB")
            return img.resize(target_size, Image.LANCZOS)
        except Exception as e:
            logger.error(f"Error resizing image {image_path}: {e}")
            return None

    @staticmethod
    def is_likely_screenshot(image_path: str) -> bool:
        """Heuristic: detect if an image is likely a screenshot.

        Screenshots tend to be:
          - PNG format (lossless)
          - 16:9 or similar widescreen aspect ratio
          - Large dimensions (≥ 1280px wide)

        This is a cheap signal used to boost tech relevance for text images.
        """
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                fmt = img.format or ""
                w, h = img.size
                aspect = w / max(h, 1)
                is_png = fmt.upper() == "PNG"
                is_widescreen = 1.3 <= aspect <= 2.0
                is_large = w >= 1280
                return is_png and is_widescreen and is_large
        except Exception:
            return False