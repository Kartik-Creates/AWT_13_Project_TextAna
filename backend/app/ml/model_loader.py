import torch
import torch.nn as nn
import logging
import os
from typing import Optional, Tuple, Any, Dict
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelLoader:
    """Singleton class to manage ML model loading and caching.

    All models are loaded lazily — nothing is loaded at import time.
    The singleton ensures each model is loaded at most once per process,
    regardless of how many times load_*() is called.

    Usage:
        from app.ml.model_loader import model_loader

        model, tokenizer = model_loader.load_roberta()
        clip_model, preprocess = model_loader.load_clip()
        nsfw_model, processor = model_loader.load_nsfw_model()
    """

    _instance: Optional["ModelLoader"] = None
    _models: Dict[str, Any] = {}

    def __new__(cls) -> "ModelLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Guard against re-initialization on subsequent __new__ hits
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"ModelLoader initialized — device: {self.device}")

        # Model cache directory (can be overridden via env var)
        self.models_dir = Path(os.getenv("MODELS_DIR", "./models"))
        self.models_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────
    #  Toxicity model (XLM-RoBERTa)
    # ──────────────────────────────────────────────────────────

    def load_roberta(self) -> Tuple[Any, Any]:
        """Load multilingual XLM-RoBERTa toxicity model and tokenizer.

        Model: unitary/multilingual-toxic-xlm-roberta
        Supports Hindi and 100+ other languages.
        Uses Jigsaw toxicity labels via sigmoid activation.
        """
        model_key = "roberta"

        if model_key in self._models:
            logger.debug("Returning cached RoBERTa model")
            return self._models[model_key]

        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        model_name = os.getenv(
            "TOXICITY_MODEL", "unitary/multilingual-toxic-xlm-roberta"
        )

        try:
            logger.info(f"🔄 Loading toxicity model: {model_name}")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            model.to(self.device)
            model.eval()

            self._models[model_key] = (model, tokenizer)
            logger.info(f"✅ Toxicity model loaded: {model_name}")
            return model, tokenizer

        except Exception as e:
            logger.error(f"❌ Could not load toxicity model {model_name}: {e}")
            raise

    # ──────────────────────────────────────────────────────────
    #  CLIP model
    # ──────────────────────────────────────────────────────────

    def load_clip(self) -> Tuple[Any, Any]:
        """Load OpenAI CLIP (ViT-B/32) for image-text relevance scoring."""
        model_key = "clip"

        if model_key in self._models:
            logger.debug("Returning cached CLIP model")
            return self._models[model_key]

        try:
            import clip

            logger.info("🔄 Loading CLIP model (ViT-B/32)...")
            model, preprocess = clip.load("ViT-B/32", device=self.device)
            model.eval()

            self._models[model_key] = (model, preprocess)
            logger.info("✅ CLIP model loaded")
            return model, preprocess

        except Exception as e:
            logger.error(f"❌ Error loading CLIP: {e}")
            raise

    # ──────────────────────────────────────────────────────────
    #  NSFW image classification model
    # ──────────────────────────────────────────────────────────

    def load_nsfw_model(self) -> Tuple[Any, Any]:
        """Load NSFW image classification model.

        Model: Falconsai/nsfw_image_detection (ViT-based)
        """
        model_key = "nsfw"

        if model_key in self._models:
            logger.debug("Returning cached NSFW model")
            return self._models[model_key]

        try:
            from transformers import AutoModelForImageClassification, ViTImageProcessor

            model_name = os.getenv("NSFW_MODEL", "Falconsai/nsfw_image_detection")
            logger.info(f"🔄 Loading NSFW model: {model_name}")

            processor = ViTImageProcessor.from_pretrained(model_name)
            model = AutoModelForImageClassification.from_pretrained(model_name)
            model.to(self.device)
            model.eval()

            self._models[model_key] = (model, processor)
            logger.info(f"✅ NSFW model loaded: {model_name}")
            return model, processor

        except Exception as e:
            logger.error(f"❌ Error loading NSFW model: {e}")
            raise

    # ──────────────────────────────────────────────────────────
    #  Lifecycle
    # ──────────────────────────────────────────────────────────

    def is_loaded(self, model_key: str) -> bool:
        """Check if a specific model is already cached."""
        return model_key in self._models

    def loaded_models(self) -> list:
        """Return a list of currently loaded model keys."""
        return list(self._models.keys())

    def unload_model(self, model_key: str) -> bool:
        """Unload a specific model to free memory.

        Returns True if the model was found and removed, False otherwise.
        """
        if model_key in self._models:
            del self._models[model_key]
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"Model '{model_key}' unloaded")
            return True
        logger.warning(f"Model '{model_key}' not found in cache")
        return False

    def unload_all(self) -> None:
        """Unload all cached models to free memory."""
        count = len(self._models)
        self._models.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info(f"All {count} model(s) unloaded")

    def get_device_info(self) -> Dict[str, Any]:
        """Return information about the current compute device."""
        info: Dict[str, Any] = {
            "device": str(self.device),
            "cuda_available": torch.cuda.is_available(),
            "loaded_models": self.loaded_models(),
        }
        if torch.cuda.is_available():
            info["cuda_device_name"] = torch.cuda.get_device_name(0)
            info["cuda_memory_allocated_mb"] = round(
                torch.cuda.memory_allocated(0) / 1024 ** 2, 2
            )
            info["cuda_memory_reserved_mb"] = round(
                torch.cuda.memory_reserved(0) / 1024 ** 2, 2
            )
        return info


# ──────────────────────────────────────────────────────────────────────────────
#  Global singleton instance
# ──────────────────────────────────────────────────────────────────────────────

model_loader = ModelLoader()