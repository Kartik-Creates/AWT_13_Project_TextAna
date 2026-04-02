import API from "./api";

/**
 * Metrics service
 * Endpoints under /api/metrics/*
 */

export const metricsService = {
  /**
   * Get aggregated model metrics
   */
  async getModelMetrics() {
    const { data } = await API.get("/api/metrics/models");
    return data;
  },

  /**
   * Get category breakdown
   */
  async getCategoryBreakdown() {
    const { data } = await API.get("/api/metrics/category-breakdown");
    return data;
  },

  /**
   * Get recent predictions
   * @param {number} limit
   */
  async getRecentPredictions(limit = 10) {
    const { data } = await API.get("/api/metrics/recent-predictions", {
      params: { limit },
    });
    return data;
  },

  /**
   * Get system health
   */
  async getSystemHealth() {
    const { data } = await API.get("/api/metrics/system-health");
    return data;
  },

  /**
   * Get advanced metrics for dashboard
   * @param {number} hours — time range
   */
  async getAdvancedMetrics(hours = 24) {
    const { data } = await API.get("/api/metrics/advanced", {
      params: { hours: Math.ceil(hours) },
    });
    return data;
  },

  /**
   * Get language distribution
   */
  async getLanguageDistribution() {
    const { data } = await API.get("/api/metrics/language-distribution");
    return data;
  },
};

export default metricsService;
