"""
Image Service — DEPRECATED
This module is superseded by the moderation pipeline's ML models:
  - app.ml.efficientnet_model  (NSFW detection)
  - app.ml.clip_model          (image-text relevance)

Kept for reference only.  Do NOT import this file in production code.
"""

import logging

logger = logging.getLogger(__name__)

logger.warning(
    "image_service.py is DEPRECATED. "
    "Use the moderation pipeline (app.services.moderation_service) instead."
)


def analyze_image(file):
    """
    DEPRECATED — always returns 'SAFE'.
    Use ModerationService.moderate_post() for real NSFW detection.
    """
    logger.warning("analyze_image() called — this function is deprecated")
    return "SAFE"