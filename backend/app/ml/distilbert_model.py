import torch
from typing import Dict, Any, List
import logging
from .model_loader import model_loader
from .text_normalizer import text_normalizer

logger = logging.getLogger(__name__)


class DistilBERTAnalyzer:
    """Text toxicity analysis using multilingual toxicity model.

    Supports English AND Hindi/Hinglish through:
      1. ML model: unitary/multilingual-toxic-xlm-roberta (or toxic-bert fallback)
         — outputs 6 Jigsaw toxicity labels via sigmoid
      2. Rule-based: Hindi abuse dictionary (text_normalizer)
         — catches slang/obfuscated abuse the ML model might miss

    The two signals are combined: if EITHER flags the text, it's toxic.
    """

    LABELS = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]

    CATEGORY_MAP = {
        "toxic": "toxic",
        "severe_toxic": "highly_toxic",
        "obscene": "sexual_content",
        "threat": "violence",
        "insult": "hate_speech",
        "identity_hate": "discrimination",
    }

    def __init__(self):
        self.model, self.tokenizer = model_loader.load_distilbert()
        self.device = model_loader.device

        # Dynamically discover labels from the model config
        id2label = getattr(self.model.config, 'id2label', None)
        if id2label:
            self.LABELS = [id2label[i] for i in sorted(id2label.keys())]
        # else: falls back to class-level LABELS

        self.label_threshold = 0.5
        self.toxicity_threshold = 0.45

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text for toxic content (English + Hindi).

        Returns dict with:
          toxicity_score, label_scores, is_toxic, category,
          flagged_labels, confidence, hindi_detection, normalized_text
        """
        try:
            # ── Step 1: Normalize obfuscated text ──
            normalized = text_normalizer.preprocess_for_model(text)

            # ── Step 2: Hindi abuse detection (rule-based) ──
            hindi_check = text_normalizer.detect_hindi_abuse(text)

            # ── Step 3: ML model inference (on normalized text) ──
            inputs = self.tokenizer(
                normalized,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.sigmoid(logits).squeeze(0)

            # Build per-label scores — handle varying number of output dims
            label_scores = {}
            flagged_labels = []
            num_outputs = probabilities.shape[0]
            for i in range(num_outputs):
                label = self.LABELS[i] if i < len(self.LABELS) else f"label_{i}"
                score = probabilities[i].item()
                label_scores[label] = round(score, 4)
                if score >= self.label_threshold:
                    flagged_labels.append(label)

            toxicity_score = max(label_scores.values())

            # ── Step 4: Boost score if Hindi abuse detected ──
            if hindi_check["has_hindi_abuse"]:
                # Take the higher of ML score and Hindi confidence
                hindi_conf = hindi_check["confidence"]
                toxicity_score = max(toxicity_score, hindi_conf)
                if "toxic" not in flagged_labels:
                    flagged_labels.append("toxic")

            # Primary category
            primary_label = max(label_scores, key=label_scores.get)
            category = self._determine_category(
                toxicity_score, primary_label, flagged_labels, hindi_check
            )

            is_toxic = (
                toxicity_score >= self.toxicity_threshold
                or len(flagged_labels) > 0
                or hindi_check["has_hindi_abuse"]
            )

            return {
                "toxicity_score": round(toxicity_score, 4),
                "label_scores": label_scores,
                "is_toxic": is_toxic,
                "category": category,
                "flagged_labels": flagged_labels,
                "confidence": round(
                    toxicity_score if is_toxic else (1.0 - toxicity_score), 4
                ),
                "flagged_phrases": [],
                "hindi_detection": hindi_check,
                "normalized_text": normalized,
            }

        except Exception as e:
            logger.error(f"Error in toxicity analysis: {e}", exc_info=True)
            return self._fallback_analysis(text)

    def _determine_category(
        self,
        score: float,
        primary_label: str,
        flagged: List[str],
        hindi_check: Dict[str, Any],
    ) -> str:
        """Map model output to a human-readable category."""
        # Hindi abuse overrides
        if hindi_check.get("has_hindi_abuse"):
            cats = hindi_check.get("categories", [])
            if any("high" in c for c in cats):
                return "hate_speech"
            return "toxic"

        if not flagged and score < self.toxicity_threshold:
            return "safe"

        severity_order = [
            "severe_toxic", "threat", "identity_hate", "toxic", "obscene", "insult"
        ]
        for label in severity_order:
            if label in flagged:
                return self.CATEGORY_MAP.get(label, label)

        return self.CATEGORY_MAP.get(
            primary_label,
            "toxic" if score > self.toxicity_threshold else "safe",
        )

    def _fallback_analysis(self, text: str) -> Dict[str, Any]:
        """Fallback: still check Hindi abuse even if model fails."""
        logger.warning("Using fallback text analysis")

        hindi_check = text_normalizer.detect_hindi_abuse(text)
        has_hindi = hindi_check["has_hindi_abuse"]

        return {
            "toxicity_score": hindi_check["confidence"] if has_hindi else 0.1,
            "label_scores": {label: 0.0 for label in self.LABELS},
            "is_toxic": has_hindi,
            "category": "hate_speech" if has_hindi else "safe",
            "flagged_labels": ["toxic"] if has_hindi else [],
            "confidence": hindi_check["confidence"] if has_hindi else 0.5,
            "flagged_phrases": [],
            "hindi_detection": hindi_check,
            "normalized_text": text_normalizer.preprocess_for_model(text),
        }


# Global instance
distilbert_analyzer = DistilBERTAnalyzer()