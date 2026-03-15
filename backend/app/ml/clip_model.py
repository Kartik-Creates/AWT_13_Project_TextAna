import os
import clip
import torch
from PIL import Image
from typing import Any, Dict, List, Optional
import logging
from .model_loader import model_loader

logger = logging.getLogger(__name__)


class CLIPAnalyzer:
    """Image-text relevance analysis using CLIP"""

    # CLIP's hard token limit
    _CLIP_TOKEN_LIMIT = 77
    # Conservative character limit to stay safely under the token limit
    _TEXT_CHAR_LIMIT = 200

    def __init__(
        self,
        relevance_threshold: float = 0.25,
        mismatch_threshold: float = 0.15,
    ):
        self.model, self.preprocess = model_loader.load_clip()
        self.device = model_loader.device

        # Configurable thresholds — previously hardcoded magic numbers
        self.relevance_threshold = relevance_threshold
        self.mismatch_threshold = mismatch_threshold

    def analyze(self, text: str, image_path: str) -> Dict[str, Any]:
        """
        Analyze relevance between text and image.
        Returns: Dict with similarity scores and analysis.
        """
        # Input validation — fail fast with clear errors
        if not text or not text.strip():
            raise ValueError("Text input cannot be empty.")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at path: {image_path}")

        try:
            # Truncate text before tokenization to respect CLIP's 77-token limit
            safe_text = self._truncate_text(text)

            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)

            # Tokenize text
            text_tokens = clip.tokenize([safe_text]).to(self.device)

            # Calculate embeddings
            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                text_features = self.model.encode_text(text_tokens)

                # Normalize features for cosine similarity
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)

                # Cosine similarity via dot product of normalized vectors
                similarity = (image_features @ text_features.T).item()

                # Get top similar concepts for additional context
                concepts = self._get_concept_similarity(image_features)

            is_relevant = similarity > self.relevance_threshold

            return {
                "similarity_score": similarity,
                "is_relevant": is_relevant,
                "relevant_concepts": concepts,
                "mismatch_detected": not is_relevant and similarity < self.mismatch_threshold,
            }

        except (FileNotFoundError, ValueError):
            # Re-raise input validation errors — do not swallow them
            raise
        except Exception as e:
            logger.error(f"Error in CLIP analysis: {e}")
            return self._fallback_analysis(text, image_path)

    def _get_concept_similarity(self, image_features: torch.Tensor) -> List[Dict[str, Any]]:
        """Get similarity with common concepts including moderation-relevant ones."""
        concepts = [
            # General visual types
            "text", "screenshot", "meme", "photo", "drawing",
            "person", "animal", "landscape", "food", "product",
            # Moderation-relevant concepts
            "violence", "graphic content", "nudity", "hate symbol", "weapon",
        ]

        try:
            concept_tokens = clip.tokenize(concepts).to(self.device)

            with torch.no_grad():
                concept_features = self.model.encode_text(concept_tokens)
                concept_features = concept_features / concept_features.norm(dim=-1, keepdim=True)

                similarities = (image_features @ concept_features.T).squeeze(0)

                # Return top 3 matching concepts
                top_indices = similarities.argsort(descending=True)[:3]

                return [
                    {"concept": concepts[idx], "score": similarities[idx].item()}
                    for idx in top_indices
                ]
        except Exception as e:
            logger.warning(f"Concept similarity computation failed: {e}")
            return []

    def _fallback_analysis(self, text: str, image_path: str) -> Dict[str, Any]:
        """Fallback analysis when CLIP inference fails."""
        logger.info("Using fallback image-text analysis")

        try:
            # PIL's verify() corrupts the file handle after use.
            # Using a context manager ensures the handle is always properly closed.
            with Image.open(image_path) as img:
                img.verify()

            return {
                "similarity_score": 0.5,
                "is_relevant": True,
                "relevant_concepts": [],
                "mismatch_detected": False,
            }
        except Exception as e:
            logger.error(f"Fallback image validation also failed: {e}")
            return {
                "similarity_score": 0.0,
                "is_relevant": False,
                "relevant_concepts": [],
                "mismatch_detected": True,
            }

    def _truncate_text(self, text: str) -> str:
        """
        Truncate text to stay safely under CLIP's 77-token hard limit.
        Logs a warning whenever truncation occurs.
        """
        if len(text) > self._TEXT_CHAR_LIMIT:
            logger.warning(
                f"Input text truncated from {len(text)} to {self._TEXT_CHAR_LIMIT} characters "
                f"to respect CLIP's {self._CLIP_TOKEN_LIMIT}-token limit."
            )
            return text[:self._TEXT_CHAR_LIMIT]
        return text


# ---------------------------------------------------------------------------
# Lazy global instance
# ---------------------------------------------------------------------------
# _clip_analyzer is None at import time — the model is NOT loaded on import.
# It is only created on the first actual call to get_clip_analyzer().
# ---------------------------------------------------------------------------
_clip_analyzer: Optional[CLIPAnalyzer] = None


def get_clip_analyzer() -> CLIPAnalyzer:
    """Return the global CLIPAnalyzer instance, creating it on first call."""
    global _clip_analyzer
    if _clip_analyzer is None:
        _clip_analyzer = CLIPAnalyzer()
    return _clip_analyzer


# ---------------------------------------------------------------------------
# Backward-compatible `clip_analyzer` name (requires Python 3.7+)
# ---------------------------------------------------------------------------
# Module-level __getattr__ is only triggered when an attribute is not found
# in the module's normal namespace. Since `clip_analyzer` is not defined as
# a variable above, any existing import like:
#
#     from your_module.clip_analyzer import clip_analyzer
#
# will route through here and return the lazily initialized instance.
# Your other files need zero changes.
# ---------------------------------------------------------------------------
def __getattr__(name: str) -> Any:
    if name == "clip_analyzer":
        return get_clip_analyzer()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")