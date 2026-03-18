from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List
import logging

from app.services.metrics_repository import metrics_repository

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/models")
async def get_model_metrics() -> Dict[str, Any]:
    """Get aggregated metrics for all models."""
    try:
        return metrics_repository.get_model_metrics()
    except Exception as e:
        logger.error(f"Error fetching model metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch model metrics")


@router.get("/language-distribution")
async def get_language_distribution() -> Dict[str, Any]:
    """Get language distribution for text predictions."""
    try:
        return metrics_repository.get_language_distribution()
    except Exception as e:
        logger.error(f"Error fetching language distribution: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch language distribution"
        )


@router.get("/category-breakdown")
async def get_category_breakdown() -> Dict[str, Any]:
    """Get content category breakdown."""
    try:
        return metrics_repository.get_category_breakdown()
    except Exception as e:
        logger.error(f"Error fetching category breakdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch category breakdown")


@router.get("/recent-predictions")
async def get_recent_predictions(limit: int = 10) -> List[Dict[str, Any]]:
    """Get most recent predictions."""
    try:
        return metrics_repository.get_recent_predictions(limit=limit)
    except Exception as e:
        logger.error(f"Error fetching recent predictions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent predictions")


@router.get("/system-health")
async def get_system_health() -> Dict[str, Any]:
    """Get overall system health metrics."""
    try:
        return metrics_repository.get_system_health()
    except Exception as e:
        logger.error(f"Error fetching system health: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch system health")


@router.get("/advanced")
async def get_advanced_metrics(hours: int = 24) -> Dict[str, Any]:
    """Get comprehensive advanced metrics for the dashboard."""
    try:
        return metrics_repository.get_advanced_metrics(hours=hours)
    except Exception as e:
        logger.error(f"Error fetching advanced metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch advanced metrics")

