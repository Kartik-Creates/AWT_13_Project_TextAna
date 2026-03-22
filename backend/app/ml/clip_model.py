import os
import clip
import torch
from PIL import Image
from typing import Any, Dict, List, Optional
import logging
from .model_loader import model_loader

logger = logging.getLogger(__name__)


class CLIPAnalyzer:
    """Image-text relevance analysis using CLIP.

    Responsibilities:
      - Measure cosine similarity between a post's text and its image
      - Detect mismatch (e.g. unrelated image attached to tech post)
      - Score image against moderation-relevant concepts
      - Score image against tech-relevant concepts (NEW)
    """

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

        self.relevance_threshold = relevance_threshold
        self.mismatch_threshold = mismatch_threshold

        # ── Concept probe sets ──
        # Used to classify what the image "looks like" via zero-shot CLIP scoring.

        # General visual types
        self.general_concepts = [
            "text", "screenshot", "meme", "photo", "drawing",
            "person", "animal", "landscape", "food", "product",
        ]

        # Harmful content concepts
        self.harmful_concepts = [
            "violence", "graphic content", "nudity", "hate symbol", "weapon",
            "blood", "gore", "explicit sexual content",
        ]

        # Tech-relevant image concepts (NEW)
        # These represent images that belong on a tech platform.
        self.tech_image_concepts = [
            "code on a screen", "terminal output", "IDE screenshot",
            "software architecture diagram", "github pull request",
            "data visualization chart", "machine learning graph",
            "circuit board hardware", "server rack datacenter",
            "developer workspace laptop", "kubernetes dashboard",
            "database schema diagram", "API documentation",
            "tech conference presentation", "programming tutorial",
        ]

        # Off-topic image concepts (NEW)
        # These represent images that clearly don't belong on a tech platform.
        self.off_topic_image_concepts = [
            "food meal restaurant", "sports game stadium",
            "celebrity fashion outfit", "beach vacation holiday",
            "wedding ceremony", "fitness workout gym",
            "religious temple church mosque",
            "political rally protest",
        ]

    def analyze(self, text: str, image_path: str) -> Dict[str, Any]:
        """Analyze relevance between text and image.

        Returns a dict with:
          - similarity_score    : float — cosine similarity between text and image embeddings
          - is_relevant         : bool — True if similarity > relevance_threshold
          - mismatch_detected   : bool — True if similarity < mismatch_threshold
          - relevant_concepts   : List[Dict] — top 3 general concept matches
          - harmful_concepts    : List[Dict] — harmful concept scores above 0.2
          - tech_image_score    : float — how "tech" the image looks (0–1)  NEW
          - is_tech_image       : bool — True if tech_image_score > 0.3      NEW
          - off_topic_image_score: float — how off-topic the image looks      NEW
        """
        if not text or not text.strip():
            raise ValueError("Text input cannot be empty.")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at path: {image_path}")

        try:
            safe_text = self._truncate_text(text)

            image = Image.open(image_path).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            text_tokens = clip.tokenize([safe_text]).to(self.device)

            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                text_features = self.model.encode_text(text_tokens)

                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)

                similarity = (image_features @ text_features.T).item()

                general_concepts = self._score_concepts(image_features, self.general_concepts, top_k=3)
                harmful_detected = self._score_harmful_concepts(image_features)
                tech_scores = self._score_tech_image(image_features)

            return {
                "similarity_score": round(similarity, 4),
                "is_relevant": similarity > self.relevance_threshold,
                "mismatch_detected": not (similarity > self.relevance_threshold)
                                     and similarity < self.mismatch_threshold,
                "relevant_concepts": general_concepts,
                "harmful_concepts": harmful_detected,
                "tech_image_score": tech_scores["tech_score"],
                "is_tech_image": tech_scores["is_tech_image"],
                "off_topic_image_score": tech_scores["off_topic_score"],
            }

        except (FileNotFoundError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Error in CLIP analysis: {e}")
            return self._fallback_analysis(text, image_path)

    def _score_concepts(
        self,
        image_features: torch.Tensor,
        concepts: List[str],
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Score image against a list of concept strings, return top_k results."""
        try:
            concept_tokens = clip.tokenize(concepts).to(self.device)

            with torch.no_grad():
                concept_features = self.model.encode_text(concept_tokens)
                concept_features = concept_features / concept_features.norm(dim=-1, keepdim=True)
                similarities = (image_features @ concept_features.T).squeeze(0)

            top_indices = similarities.argsort(descending=True)[:top_k]
            return [
                {"concept": concepts[idx], "score": round(similarities[idx].item(), 4)}
                for idx in top_indices
            ]
        except Exception as e:
            logger.warning(f"Concept scoring failed: {e}")
            return []

    def _score_harmful_concepts(self, image_features: torch.Tensor) -> List[Dict[str, Any]]:
        """Return harmful concepts with score above 0.20 (flagging threshold)."""
        try:
            all_scores = self._score_concepts(image_features, self.harmful_concepts, top_k=len(self.harmful_concepts))
            return [c for c in all_scores if c["score"] > 0.20]
        except Exception as e:
            logger.warning(f"Harmful concept scoring failed: {e}")
            return []

    def _score_tech_image(self, image_features: torch.Tensor) -> Dict[str, Any]:
        """Score the image against tech and off-topic concept sets.

        Returns:
          tech_score      : float (0–1) — higher = more tech-looking image
          off_topic_score : float (0–1) — higher = more off-topic-looking image
          is_tech_image   : bool
        """
        try:
            tech_scores = self._score_concepts(
                image_features, self.tech_image_concepts, top_k=len(self.tech_image_concepts)
            )
            off_topic_scores = self._score_concepts(
                image_features, self.off_topic_image_concepts, top_k=len(self.off_topic_image_concepts)
            )

            # Average of top-3 scores for each set
            top_tech = sorted(tech_scores, key=lambda x: x["score"], reverse=True)[:3]
            top_off = sorted(off_topic_scores, key=lambda x: x["score"], reverse=True)[:3]

            tech_avg = sum(c["score"] for c in top_tech) / max(len(top_tech), 1)
            off_avg = sum(c["score"] for c in top_off) / max(len(top_off), 1)

            # Normalize both to 0–1 using the CLIP similarity range
            # CLIP cosine sims typically sit in 0.15–0.35 for zero-shot concepts
            # We scale by dividing by 0.35 and capping at 1.0
            tech_score = round(min(tech_avg / 0.35, 1.0), 4)
            off_topic_score = round(min(off_avg / 0.35, 1.0), 4)

            return {
                "tech_score": tech_score,
                "off_topic_score": off_topic_score,
                "is_tech_image": tech_score > 0.3,
                "top_tech_concepts": top_tech[:2],
                "top_off_topic_concepts": top_off[:2],
            }
        except Exception as e:
            logger.warning(f"Tech image scoring failed: {e}")
            return {
                "tech_score": 0.0,
                "off_topic_score": 0.0,
                "is_tech_image": False,
                "top_tech_concepts": [],
                "top_off_topic_concepts": [],
            }

    def _fallback_analysis(self, text: str, image_path: str) -> Dict[str, Any]:
        """Fallback analysis when CLIP inference fails."""
        logger.info("Using fallback image-text analysis")
        try:
            with Image.open(image_path) as img:
                img.verify()
            return {
                "similarity_score": 0.5,
                "is_relevant": True,
                "mismatch_detected": False,
                "relevant_concepts": [],
                "harmful_concepts": [],
                "tech_image_score": 0.0,
                "is_tech_image": False,
                "off_topic_image_score": 0.0,
            }
        except Exception as e:
            logger.error(f"Fallback image validation also failed: {e}")
            return {
                "similarity_score": 0.0,
                "is_relevant": False,
                "mismatch_detected": True,
                "relevant_concepts": [],
                "harmful_concepts": [],
                "tech_image_score": 0.0,
                "is_tech_image": False,
                "off_topic_image_score": 0.0,
            }

    def _truncate_text(self, text: str) -> str:
        """Truncate text to respect CLIP's 77-token hard limit."""
        if len(text) > self._TEXT_CHAR_LIMIT:
            logger.warning(
                f"Input text truncated from {len(text)} to {self._TEXT_CHAR_LIMIT} characters "
                f"to respect CLIP's {self._CLIP_TOKEN_LIMIT}-token limit."
            )
            return text[:self._TEXT_CHAR_LIMIT]
        return text


# ──────────────────────────────────────────────────────────────────────────────
#  Lazy global instance
# ──────────────────────────────────────────────────────────────────────────────

_clip_analyzer: Optional[CLIPAnalyzer] = None


def get_clip_analyzer() -> CLIPAnalyzer:
    """Return the global CLIPAnalyzer instance, creating it on first call."""
    global _clip_analyzer
    if _clip_analyzer is None:
        _clip_analyzer = CLIPAnalyzer()
    return _clip_analyzer


def __getattr__(name: str) -> Any:
    """Module-level __getattr__ for backward-compatible `clip_analyzer` import."""
    if name == "clip_analyzer":
        return get_clip_analyzer()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")