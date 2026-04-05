"""
Unified Moderation Service - Switch between Ensemble and Ollama approaches
Set MODERATION_APPROACH=ensemble (default) or MODERATION_APPROACH=ollama
"""

import os
import logging

logger = logging.getLogger(__name__)

MODERATION_APPROACH = os.getenv("MODERATION_APPROACH", "ensemble").lower()
logger.info(f"🔀 Moderation approach selected: {MODERATION_APPROACH}")

if MODERATION_APPROACH == "ollama":
    from app.services._moderation_service_ollama import ModerationService
    logger.info("✅ Loaded: Ollama (LLM-based) moderation service")
else:
    from app.services._moderation_service_ensemble import ModerationService
    logger.info("✅ Loaded: Ensemble (multi-model) moderation service")

__all__ = ["ModerationService"]
