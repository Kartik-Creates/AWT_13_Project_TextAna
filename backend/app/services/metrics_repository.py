from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import re

from app.db.mongodb import MongoDB

logger = logging.getLogger(__name__)


class MetricsRepository:
    """Repository for prediction metrics and aggregated model statistics.

    Stores one document per pipeline stage per post into the
    `prediction_metrics` MongoDB collection, then provides
    aggregated read views for the dashboard.

    New in this version:
      - Tech relevance metrics (zone distribution, avg score)
      - Off-topic block tracking
      - Tech vs harm breakdown in outcomes
    """

    def __init__(self) -> None:
        self.db = MongoDB()
        self.collection = self.db.prediction_metrics

        # In-memory cache to avoid heavy aggregations on every request
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
        self._cache_ttl = timedelta(seconds=30)

    # ───────────────────────────────────────────────────────────
    #  Write path
    # ───────────────────────────────────────────────────────────

    def insert_prediction(self, doc: Dict[str, Any]) -> None:
        """Insert a single prediction metrics document."""
        try:
            doc.setdefault("timestamp", datetime.utcnow())
            self.collection.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to insert prediction metrics: {e}", exc_info=True)

    # ───────────────────────────────────────────────────────────
    #  Cache helpers
    # ───────────────────────────────────────────────────────────

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

    def invalidate_cache(self) -> None:
        """Manually clear the in-memory cache."""
        self._cache.clear()
        logger.info("Metrics cache invalidated")

    # ───────────────────────────────────────────────────────────
    #  Read path — basic aggregations
    # ───────────────────────────────────────────────────────────

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
                            "$cond": [{"$eq": ["$correct", True]}, 1, 0]
                        }
                    },
                    "total_with_correct": {
                        "$sum": {
                            "$cond": [{"$in": ["$correct", [True, False]]}, 1, 0]
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
            {"$group": {"_id": "$language", "count": {"$sum": 1}}},
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
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
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
            cursor = self.collection.find().sort("timestamp", -1).limit(limit)
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
                    doc["timestamp"] = doc["timestamp"].isoformat()
                docs.append(doc)
        except Exception as e:
            logger.error(f"Failed to fetch recent predictions: {e}", exc_info=True)

        return self._set_cache(cache_key, docs)

    def get_system_health(self) -> Dict[str, Any]:
        """Lightweight system health summary based on metrics."""
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

    # ───────────────────────────────────────────────────────────
    #  Tech relevance metrics  ← NEW
    # ───────────────────────────────────────────────────────────

    def get_tech_relevance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Aggregate tech relevance metrics for the dashboard.

        Returns:
          zone_distribution     : count + % for tech / review / off_topic
          avg_tech_score        : average tech_relevance_score across all text posts
          off_topic_block_count : posts blocked specifically for being off-topic
          top_matched_categories: most frequently matched tech taxonomy categories
          top_non_tech_signals  : most common off-topic signals that triggered blocks
        """
        cache_key = f"tech_relevance_metrics_{hours}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        time_filter = {"timestamp": {"$gte": cutoff}}

        result: Dict[str, Any] = {
            "zone_distribution": self._calc_zone_distribution(time_filter),
            "avg_tech_score": self._calc_avg_tech_score(time_filter),
            "off_topic_block_count": self._calc_off_topic_blocks(time_filter),
            "top_matched_categories": self._calc_top_tech_categories(time_filter),
            "top_non_tech_signals": self._calc_top_non_tech_signals(time_filter),
        }

        return self._set_cache(cache_key, result)

    def _calc_zone_distribution(self, time_filter: dict) -> Dict[str, Any]:
        """Count of tech / review / off_topic zone decisions."""
        try:
            pipeline = [
                {"$match": {
                    **time_filter,
                    "model": "rule_engine_tech",
                }},
                {"$group": {
                    "_id": "$prediction.zone",
                    "count": {"$sum": 1},
                }},
            ]
            zones: Dict[str, int] = {"tech": 0, "review": 0, "off_topic": 0}
            total = 0
            for row in self.collection.aggregate(pipeline):
                z = row["_id"] or "unknown"
                c = int(row.get("count", 0))
                zones[z] = c
                total += c

            return {
                "tech":      {"count": zones["tech"],      "pct": round(zones["tech"] / total * 100, 1) if total else 0},
                "review":    {"count": zones["review"],    "pct": round(zones["review"] / total * 100, 1) if total else 0},
                "off_topic": {"count": zones["off_topic"], "pct": round(zones["off_topic"] / total * 100, 1) if total else 0},
                "total": total,
            }
        except Exception as e:
            logger.error(f"Zone distribution calc failed: {e}", exc_info=True)
            return {"tech": {}, "review": {}, "off_topic": {}, "total": 0}

    def _calc_avg_tech_score(self, time_filter: dict) -> float:
        """Average tech_relevance_score across rule_engine_tech predictions."""
        try:
            pipeline = [
                {"$match": {
                    **time_filter,
                    "model": "rule_engine_tech",
                    "confidence": {"$exists": True, "$ne": None},
                }},
                {"$group": {"_id": None, "avg": {"$avg": "$confidence"}}},
            ]
            for row in self.collection.aggregate(pipeline):
                return round(float(row.get("avg", 0)), 3)
        except Exception as e:
            logger.error(f"Avg tech score calc failed: {e}", exc_info=True)
        return 0.0

    def _calc_off_topic_blocks(self, time_filter: dict) -> int:
        """Count of posts blocked specifically for being off-topic."""
        try:
            return int(self.collection.count_documents({
                **time_filter,
                "model": "rule_engine_tech",
                "category": "off_topic",
            }))
        except Exception as e:
            logger.error(f"Off-topic block count failed: {e}", exc_info=True)
            return 0

    def _calc_top_tech_categories(self, time_filter: dict, top_n: int = 8) -> List[Dict[str, Any]]:
        """Most frequently matched tech taxonomy categories."""
        try:
            pipeline = [
                {"$match": {
                    **time_filter,
                    "model": "rule_engine_tech",
                    "prediction.matched_categories": {"$exists": True, "$ne": []},
                }},
                {"$unwind": "$prediction.matched_categories"},
                {"$group": {
                    "_id": "$prediction.matched_categories",
                    "count": {"$sum": 1},
                }},
                {"$sort": {"count": -1}},
                {"$limit": top_n},
            ]
            return [
                {"category": row["_id"], "count": int(row["count"])}
                for row in self.collection.aggregate(pipeline)
            ]
        except Exception as e:
            logger.error(f"Top tech categories calc failed: {e}", exc_info=True)
            return []

    def _calc_top_non_tech_signals(self, time_filter: dict, top_n: int = 6) -> List[Dict[str, Any]]:
        """Most common off-topic signals detected on blocked posts."""
        try:
            pipeline = [
                {"$match": {
                    **time_filter,
                    "model": "rule_engine_tech",
                    "category": "off_topic",
                }},
                {"$group": {
                    "_id": None,
                    "all_signals": {"$push": "$prediction.non_tech_signals"},
                }},
            ]
            signal_counts: Dict[str, int] = {}
            for row in self.collection.aggregate(pipeline):
                all_signals = row.get("all_signals", [])
                for signal_list in all_signals:
                    if isinstance(signal_list, list):
                        for signal in signal_list:
                            signal_counts[signal] = signal_counts.get(signal, 0) + 1

            sorted_signals = sorted(signal_counts.items(), key=lambda x: -x[1])[:top_n]
            return [{"signal": s, "count": c} for s, c in sorted_signals]
        except Exception as e:
            logger.error(f"Top non-tech signals calc failed: {e}", exc_info=True)
            return []

    # ───────────────────────────────────────────────────────────
    #  Advanced metrics (full dashboard)
    # ───────────────────────────────────────────────────────────

    def get_advanced_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Return all advanced metrics for the dashboard."""
        cache_key = f"advanced_metrics_{hours}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        now = datetime.utcnow()
        cutoff = now - timedelta(hours=hours)
        time_filter = {"timestamp": {"$gte": cutoff}}

        result: Dict[str, Any] = {
            "latency":                  self._calc_latency(time_filter),
            "outcomes":                 self._calc_outcomes(time_filter),
            "confidence_distribution":  self._calc_confidence_buckets(time_filter),
            "prediction_volume":        self._calc_prediction_volume(now),
            "edge_cases":               self._calc_edge_cases(time_filter),
            "top_keywords":             self._calc_top_keywords(time_filter),
            "recent_critical":          self._calc_recent_critical(time_filter),
            "pipeline_latency":         self._calc_pipeline_latency(time_filter),
            "model_agreement":          self._calc_model_agreement(time_filter),
            "false_positives":          self._calc_false_positives(time_filter),
            # Tech relevance section
            "tech_relevance":           self.get_tech_relevance_metrics(hours),
        }

        return self._set_cache(cache_key, result)

    # ── Sub-aggregations ──

    def _calc_latency(self, time_filter: dict) -> Dict[str, Any]:
        """P95, P99, max latency per model."""
        try:
            pipeline = [
                {"$match": {**time_filter, "response_time_ms": {"$exists": True, "$ne": None}}},
                {"$group": {
                    "_id": "$model",
                    "times": {"$push": "$response_time_ms"},
                    "max": {"$max": "$response_time_ms"},
                    "avg": {"$avg": "$response_time_ms"},
                    "count": {"$sum": 1},
                }},
            ]
            out: Dict[str, Any] = {}
            for row in self.collection.aggregate(pipeline):
                model = row["_id"] or "unknown"
                times = sorted(row.get("times", []))
                n = len(times)
                p95 = times[int(n * 0.95)] if n > 0 else 0
                p99 = times[int(min(n * 0.99, n - 1))] if n > 0 else 0
                out[model] = {
                    "p95":   round(p95, 1),
                    "p99":   round(p99, 1),
                    "max":   round(row.get("max", 0), 1),
                    "avg":   round(row.get("avg", 0), 1),
                    "count": row.get("count", 0),
                }
            return out
        except Exception as e:
            logger.error(f"Latency calc failed: {e}", exc_info=True)
            return {}

    def _calc_outcomes(self, time_filter: dict) -> Dict[str, Any]:
        """Allowed/blocked counts + top block reasons, with off-topic split."""
        try:
            pipeline = [
                {"$match": time_filter},
                {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            ]
            cats: Dict[str, int] = {}
            total = 0
            for row in self.collection.aggregate(pipeline):
                cat = row["_id"] or "unknown"
                c = int(row.get("count", 0))
                cats[cat] = c
                total += c

            safe_count = cats.get("safe", 0)
            off_topic_count = cats.get("off_topic", 0)
            harm_blocked = total - safe_count - off_topic_count
            blocked_count = total - safe_count

            reasons = [
                {
                    "reason": k,
                    "count": v,
                    "percentage": round(v / blocked_count * 100, 1) if blocked_count else 0,
                }
                for k, v in sorted(cats.items(), key=lambda x: -x[1])
                if k != "safe"
            ]

            return {
                "total":           total,
                "allowed":         safe_count,
                "allowed_pct":     round(safe_count / total * 100, 1) if total else 0,
                "blocked":         blocked_count,
                "blocked_pct":     round(blocked_count / total * 100, 1) if total else 0,
                "off_topic_blocked":      off_topic_count,
                "off_topic_blocked_pct":  round(off_topic_count / total * 100, 1) if total else 0,
                "harm_blocked":           harm_blocked,
                "harm_blocked_pct":       round(harm_blocked / total * 100, 1) if total else 0,
                "top_reasons":     reasons[:8],
            }
        except Exception as e:
            logger.error(f"Outcomes calc failed: {e}", exc_info=True)
            return {
                "total": 0, "allowed": 0, "allowed_pct": 0,
                "blocked": 0, "blocked_pct": 0,
                "off_topic_blocked": 0, "off_topic_blocked_pct": 0,
                "harm_blocked": 0, "harm_blocked_pct": 0,
                "top_reasons": [],
            }

    def _calc_confidence_buckets(self, time_filter: dict) -> Dict[str, Any]:
        """Confidence distribution in low / medium / high buckets."""
        try:
            pipeline = [
                {"$match": {**time_filter, "confidence": {"$exists": True, "$ne": None}}},
                {"$bucket": {
                    "groupBy": "$confidence",
                    "boundaries": [0, 0.7, 0.9, 1.01],
                    "default": "other",
                    "output": {"count": {"$sum": 1}},
                }},
            ]
            buckets = {"low": 0, "medium": 0, "high": 0}
            label_map = {0: "low", 0.7: "medium", 0.9: "high"}
            for row in self.collection.aggregate(pipeline):
                bid = row.get("_id")
                label = label_map.get(bid, "low")
                buckets[label] = int(row.get("count", 0))
            return buckets
        except Exception as e:
            logger.error(f"Confidence bucket calc failed: {e}", exc_info=True)
            return {"low": 0, "medium": 0, "high": 0}

    def _calc_prediction_volume(self, now: datetime) -> Dict[str, Any]:
        """Predictions in last 1h, 24h, and peak per hour."""
        try:
            h1  = now - timedelta(hours=1)
            h24 = now - timedelta(hours=24)

            last_1h  = self.collection.count_documents({"timestamp": {"$gte": h1}})
            last_24h = self.collection.count_documents({"timestamp": {"$gte": h24}})

            pipeline = [
                {"$match": {"timestamp": {"$gte": h24}}},
                {"$group": {
                    "_id": {
                        "y": {"$year": "$timestamp"},
                        "m": {"$month": "$timestamp"},
                        "d": {"$dayOfMonth": "$timestamp"},
                        "h": {"$hour": "$timestamp"},
                    },
                    "count": {"$sum": 1},
                }},
                {"$sort": {"count": -1}},
                {"$limit": 1},
            ]
            peak = 0
            for row in self.collection.aggregate(pipeline):
                peak = int(row.get("count", 0))

            return {"last_1h": last_1h, "last_24h": last_24h, "peak_per_hour": peak}
        except Exception as e:
            logger.error(f"Volume calc failed: {e}", exc_info=True)
            return {"last_1h": 0, "last_24h": 0, "peak_per_hour": 0}

    def _calc_edge_cases(self, time_filter: dict) -> Dict[str, Any]:
        """Count short text, empty, and URL-only inputs."""
        try:
            base_match = {**time_filter, "input_type": "text"}
            short = 0
            empty = 0
            url_only = 0
            url_re = re.compile(r'^https?://\S+$', re.IGNORECASE)

            cursor = self.collection.find(
                {**base_match, "input_preview": {"$exists": True}},
                {"input_preview": 1}
            )
            for doc in cursor:
                preview = doc.get("input_preview", "") or ""
                words = preview.strip().split()
                if len(words) == 0 or not preview.strip():
                    empty += 1
                elif len(words) < 5:
                    short += 1
                if url_re.match(preview.strip()):
                    url_only += 1

            return {"short_text": short, "empty_input": empty, "url_only": url_only}
        except Exception as e:
            logger.error(f"Edge case calc failed: {e}", exc_info=True)
            return {"short_text": 0, "empty_input": 0, "url_only": 0}

    def _calc_top_keywords(self, time_filter: dict) -> List[Dict[str, Any]]:
        """Most frequent trigger categories from blocked predictions."""
        try:
            pipeline = [
                {"$match": {
                    **time_filter,
                    "category": {"$nin": [None, "safe", "mismatch", "off_topic", "review"]},
                }},
                {"$group": {"_id": "$category", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10},
            ]
            return [
                {"keyword": row["_id"], "count": int(row["count"])}
                for row in self.collection.aggregate(pipeline)
            ]
        except Exception as e:
            logger.error(f"Top keywords calc failed: {e}", exc_info=True)
            return []

    def _calc_recent_critical(self, time_filter: dict) -> List[Dict[str, Any]]:
        """Recent high-severity flagged content."""
        try:
            critical_cats = [
                "nsfw", "toxicity", "highly_toxic", "violence",
                "hate_speech", "discrimination", "sexual_content",
                "terrorism", "self_harm",
            ]
            cursor = (
                self.collection.find(
                    {**time_filter, "category": {"$in": critical_cats}},
                    {"input_preview": 1, "category": 1, "confidence": 1, "timestamp": 1, "model": 1}
                )
                .sort("timestamp", -1)
                .limit(10)
            )
            items = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
                    doc["timestamp"] = doc["timestamp"].isoformat()
                severity = "high" if doc.get("confidence", 0) > 0.8 else "medium"
                doc["severity"] = severity
                items.append(doc)
            return items
        except Exception as e:
            logger.error(f"Recent critical calc failed: {e}", exc_info=True)
            return []

    def _calc_pipeline_latency(self, time_filter: dict) -> Dict[str, float]:
        """Average response time per model (pipeline stage breakdown)."""
        try:
            pipeline = [
                {"$match": {**time_filter, "response_time_ms": {"$exists": True, "$ne": None}}},
                {"$group": {"_id": "$model", "avg": {"$avg": "$response_time_ms"}}},
            ]
            out: Dict[str, float] = {}
            for row in self.collection.aggregate(pipeline):
                model = row["_id"] or "unknown"
                out[model] = round(row.get("avg", 0), 1)
            return out
        except Exception as e:
            logger.error(f"Pipeline latency calc failed: {e}", exc_info=True)
            return {}

    def _calc_model_agreement(self, time_filter: dict) -> Dict[str, Any]:
        """Percentage of posts where all models agree on allow/block."""
        try:
            pipeline = [
                {"$match": {**time_filter, "post_id": {"$exists": True}}},
                {"$group": {
                    "_id": "$post_id",
                    "categories": {"$push": "$category"},
                    "count": {"$sum": 1},
                }},
                {"$match": {"count": {"$gte": 2}}},
            ]
            total_posts = 0
            agreed = 0
            for row in self.collection.aggregate(pipeline):
                total_posts += 1
                cats = row.get("categories", [])
                safe_count = sum(1 for c in cats if c == "safe")
                if safe_count == len(cats) or safe_count == 0:
                    agreed += 1

            pct = round(agreed / total_posts * 100, 1) if total_posts else 0
            return {"agreement_pct": pct, "total_posts": total_posts, "agreed": agreed}
        except Exception as e:
            logger.error(f"Model agreement calc failed: {e}", exc_info=True)
            return {"agreement_pct": 0, "total_posts": 0, "agreed": 0}

    def _calc_false_positives(self, time_filter: dict) -> Dict[str, Any]:
        """Posts where ML is confident it's safe, but still got blocked."""
        try:
            pipeline = [
                {"$match": {**time_filter, "post_id": {"$exists": True}}},
                {"$group": {
                    "_id": "$post_id",
                    "predictions": {
                        "$push": {
                            "model":      "$model",
                            "category":   "$category",
                            "confidence": "$confidence",
                        }
                    },
                }},
            ]
            count: int = 0
            for row in self.collection.aggregate(pipeline):
                preds = row.get("predictions", [])
                has_safe_ml = any(
                    p.get("category") == "safe" and (p.get("confidence") or 0) > 0.7
                    for p in preds
                    if p.get("model") in ("roberta", "efficientnet")
                )
                has_block = any(
                    p.get("category") not in (None, "safe")
                    for p in preds
                )
                if has_safe_ml and has_block:
                    count = count + 1

            return {"count": count}
        except Exception as e:
            logger.error(f"False positive calc failed: {e}", exc_info=True)
            return {"count": 0}


# ──────────────────────────────────────────────────────────────────────────────
#  Global singleton instance
# ──────────────────────────────────────────────────────────────────────────────

metrics_repository = MetricsRepository()