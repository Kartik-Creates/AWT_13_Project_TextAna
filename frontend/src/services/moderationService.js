import API from "./api";

/**
 * Moderation service
 * Endpoints under /moderation/*
 */

export const moderationService = {
  /**
   * Get moderation status for a specific post
   * @param {string} postId
   */
  async getModerationStatus(postId) {
    const { data } = await API.get(`/moderation/status/${postId}`);
    return data;
  },

  /**
   * Get moderation statistics
   * @param {number} days — number of days to look back
   */
  async getModerationStats(days = 7) {
    const { data } = await API.get("/moderation/stats", {
      params: { days },
    });
    return data;
  },

  /**
   * Get advanced/detailed metrics
   */
  async getAdvancedMetrics() {
    const { data } = await API.get("/moderation/stats/advanced");
    return data;
  },

  /**
   * Get recent predictions
   * @param {number} limit
   */
  async getRecentPredictions(limit = 10) {
    const { data } = await API.get("/moderation/recent-predictions", {
      params: { limit },
    });
    return data;
  },

  /**
   * Get category breakdown
   */
  async getCategoryBreakdown() {
    const { data } = await API.get("/moderation/category-breakdown");
    return data;
  },

  /**
   * Get system health info
   */
  async getSystemHealth() {
    const { data } = await API.get("/moderation/system-health");
    return data;
  },
};

export default moderationService;
