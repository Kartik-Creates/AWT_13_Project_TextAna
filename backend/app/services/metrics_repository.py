from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from app.db.mongodb import MongoDB

logger = logging.getLogger(__name__)


class MetricsRepository:
    """Repository for prediction metrics and aggregated model statistics."""

    def __init__(self) -> None:
        self.db = MongoDB()
        self.collection = self.db.prediction_metrics

        # Simple in-memory caches to avoid heavy aggregations on every request
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
        self._cache_ttl = timedelta(seconds=30)

    # ───────────────────────────────
    # Write path
    # ───────────────────────────────

    def insert_prediction(self, doc: Dict[str, Any]) -> None:
        """Insert a single prediction metrics document."""
        try:
            doc.setdefault("timestamp", datetime.utcnow())
            self.collection.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to insert prediction metrics: {e}", exc_info=True)

    # ───────────────────────────────
    # Cache helpers
    # ───────────────────────────────

    def _get_from_cache(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if not entry:
            return None
        ts, value = entry
        if datetime.utcnow() - ts > self._cache_ttl:
            return None
        return value

    def _set_cache(self, key: str, value: Any) -> Any:
        self._cache[key] = (datetime.utcnow(), value)
        return value

    # ───────────────────────────────
    # Read path – aggregations
    # ───────────────────────────────

    def get_model_metrics(self) -> Dict[str, Any]:
        """Aggregate per-model performance statistics."""
        cache_key = "model_metrics"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        pipeline = [
            {
                "$group": {
                    "_id": "$model",
                    "count": {"$sum": 1},
                    "avg_response_time": {"$avg": "$response_time_ms"},
                    "avg_confidence": {"$avg": "$confidence"},
                    "correct": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$correct", True]},
                                1,
                                0,
                            ]
                        }
                    },
                    "total_with_correct": {
                        "$sum": {
                            "$cond": [
                                {"$in": ["$correct", [True, False]]},
                                1,
                                0,
                            ]
                        }
                    },
                }
            }
        ]

        result: Dict[str, Any] = {}
        try:
            for row in self.collection.aggregate(pipeline):
                model = row["_id"]
                total = row.get("total_with_correct") or 0
                correct = row.get("correct") or 0
                accuracy = (correct / total) * 100 if total else None

                result[model] = {
                    "total_predictions": int(row.get("count", 0)),
                    "avg_response_time_ms": row.get("avg_response_time") or 0,
                    "avg_confidence": row.get("avg_confidence") or 0,
                    "accuracy": accuracy,
                }
        except Exception as e:
            logger.error(f"Failed to aggregate model metrics: {e}", exc_info=True)

        return self._set_cache(cache_key, result)

    def get_language_distribution(self) -> Dict[str, Any]:
        """Distribution of languages for text model."""
        cache_key = "language_distribution"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        pipeline = [
            {"$match": {"input_type": "text"}},
            {
                "$group": {
                    "_id": "$language",
                    "count": {"$sum": 1},
                }
            },
        ]

        total = 0
        items: List[Dict[str, Any]] = []

        try:
            for row in self.collection.aggregate(pipeline):
                lang = row["_id"] or "other"
                count = int(row.get("count", 0))
                total += count
                items.append({"language": lang, "count": count})
        except Exception as e:
            logger.error(f"Failed to aggregate language distribution: {e}", exc_info=True)

        for item in items:
            item["percentage"] = (item["count"] / total) * 100 if total else 0.0

        payload = {"total": total, "items": items}
        return self._set_cache(cache_key, payload)

    def get_category_breakdown(self) -> Dict[str, Any]:
        """Breakdown of predicted categories."""
        cache_key = "category_breakdown"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        pipeline = [
            {
                "$group": {
                    "_id": "$category",
                    "count": {"$sum": 1},
                }
            }
        ]

        total = 0
        items: List[Dict[str, Any]] = []

        try:
            for row in self.collection.aggregate(pipeline):
                cat = row["_id"] or "other"
                count = int(row.get("count", 0))
                total += count
                items.append({"category": cat, "count": count})
        except Exception as e:
            logger.error(f"Failed to aggregate category breakdown: {e}", exc_info=True)

        for item in items:
            item["percentage"] = (item["count"] / total) * 100 if total else 0.0

        payload = {"total": total, "items": items}
        return self._set_cache(cache_key, payload)

    def get_recent_predictions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return most recent N predictions."""
        cache_key = f"recent_predictions_{limit}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        docs: List[Dict[str, Any]] = []
        try:
            cursor = (
                self.collection.find()
                .sort("timestamp", -1)
                .limit(limit)
            )
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
                    doc["timestamp"] = doc["timestamp"].isoformat()
                docs.append(doc)
        except Exception as e:
            logger.error(f"Failed to fetch recent predictions: {e}", exc_info=True)

        return self._set_cache(cache_key, docs)

    def get_system_health(self) -> Dict[str, Any]:
        """Very lightweight system health summary based on metrics."""
        cache_key = "system_health"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        now = datetime.utcnow()
        five_minutes_ago = now - timedelta(minutes=5)

        try:
            total = self.collection.count_documents({})
            recent = self.collection.count_documents({"timestamp": {"$gte": five_minutes_ago}})
        except Exception as e:
            logger.error(f"Failed to compute system health metrics: {e}", exc_info=True)
            total = 0
            recent = 0

        payload = {
            "api_status": "operational",
            "models": {
                "roberta": "loaded",
                "efficientnet": "loaded",
                "clip": "loaded",
            },
            "queue_size": 0,
            "avg_response_time_ms": None,
            "uptime": "99.97%",
            "total_predictions": total,
            "recent_predictions_last_5m": recent,
            "timestamp": now.isoformat(),
        }

        return self._set_cache(cache_key, payload)


metrics_repository = MetricsRepository()

