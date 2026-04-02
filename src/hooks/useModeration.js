import { useState, useEffect, useCallback } from "react";
import metricsService from "../services/metricsService";

const POLL_INTERVAL_MS = 30000;

/**
 * Custom hook for moderation / metrics dashboard data
 * Fetches all metric endpoints in parallel and auto-refreshes every 30 seconds.
 */
export function useModeration(timeRange = 24) {
  const [modelMetrics, setModelMetrics] = useState(null);
  const [categoryBreakdown, setCategoryBreakdown] = useState(null);
  const [recentPredictions, setRecentPredictions] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [advancedMetrics, setAdvancedMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      const [models, categories, recent, health, advanced] =
        await Promise.all([
          metricsService.getModelMetrics().catch(() => null),
          metricsService.getCategoryBreakdown().catch(() => null),
          metricsService.getRecentPredictions(10).catch(() => []),
          metricsService.getSystemHealth().catch(() => null),
          metricsService.getAdvancedMetrics(timeRange).catch(() => null),
        ]);

      if (models) setModelMetrics(models);
      if (categories) setCategoryBreakdown(categories);
      setRecentPredictions(Array.isArray(recent) ? recent : []);
      if (health) setSystemHealth(health);
      if (advanced) setAdvancedMetrics(advanced);
      setError(null);
    } catch (err) {
      console.error("Failed to load metrics dashboard data", err);
      setError("Failed to load metrics");
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    setLoading(true);
    fetchAll();
    const id = setInterval(fetchAll, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchAll]);

  return {
    modelMetrics,
    categoryBreakdown,
    recentPredictions,
    systemHealth,
    advancedMetrics,
    loading,
    error,
    refresh: fetchAll,
  };
}

export default useModeration;
