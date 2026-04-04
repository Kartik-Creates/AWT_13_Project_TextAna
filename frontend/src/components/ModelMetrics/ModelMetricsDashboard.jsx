import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";

// Existing components
import ConfusionMatrix from "./ConfusionMatrix";
import CategoryBarChart from "./CategoryBarChart";
import RecentPredictionsTable from "./RecentPredictionsTable";
import SystemHealthCard from "./SystemHealthCard";

// Utility components
import DashboardFilters from "./DashboardFilters";
import LatencyMetrics from "./LatencyMetrics";
import ModerationOutcome from "./ModerationOutcome";
import FalsePositiveIndicator from "./FalsePositiveIndicator";
import ConfidenceDistribution from "./ConfidenceDistribution";
import PredictionVolume from "./PredictionVolume";
import PipelineLatency from "./PipelineLatency";
import ModelAgreement from "./ModelAgreement";
import EdgeCaseDetector from "./EdgeCaseDetector";
import TopTriggerKeywords from "./TopTriggerKeywords";
import RecentCriticalFlags from "./RecentCriticalFlags";

// ── New model-aware components ──
import SemanticRelevanceGraph from "./SemanticRelevanceGraph";
import ToxicityBreakdownChart from "./ToxicityBreakdownChart";
import HateSpeechMetricsCard from "./HateSpeechMetricsCard";
import ImageAnalysisMetrics from "./ImageAnalysisMetrics";

import metricsService from "../../services/metricsService";

const POLL_INTERVAL_MS = 30000;

export default function ModelMetricsDashboard() {
  const [modelMetrics, setModelMetrics] = useState(null);
  const [categoryBreakdown, setCategoryBreakdown] = useState(null);
  const [recentPredictions, setRecentPredictions] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [advancedMetrics, setAdvancedMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  // Dashboard filter state
  const [timeRange, setTimeRange] = useState(24);       // hours
  const [categoryFilter, setCategoryFilter] = useState("all");

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
    } catch (err) {
      console.error("Failed to load metrics dashboard data", err);
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

  // REMOVED: robertaStats, efficientnetStats, clipStats - no longer needed

  // Filter recent predictions by category
  const filteredPredictions = recentPredictions.filter((p) => {
    if (categoryFilter === "all") return true;
    if (categoryFilter === "blocked") return p.category !== "safe";
    if (categoryFilter === "spam") return p.category === "spam";
    if (categoryFilter === "nsfw") return p.category === "nsfw";
    if (categoryFilter === "high") return (p.confidence || 0) > 0.8 && p.category !== "safe";
    return true;
  });

  const handleExport = async (format = "json") => {
    const payload = {
      modelMetrics,
      categoryBreakdown,
      recentPredictions,
      systemHealth,
      advancedMetrics,
    };

    if (format === "json") {
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "model-metrics.json";
      a.click();
      URL.revokeObjectURL(url);
    } else if (format === "csv") {
      const header = "id,model,input_type,category,response_time_ms\n";
      const rows =
        recentPredictions
          ?.map((p, idx) => `${idx + 1},${p.model},${p.input_type},${p.category || ""},${p.response_time_ms || ""}`)
          .join("\n") || "";
      const blob = new Blob([header + rows], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "recent-predictions.csv";
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const stagger = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.08 } },
  };
  const fadeUp = {
    hidden: { opacity: 0, y: 18 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
  };

  return (
    <div className="space-y-8">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            Moderation Analytics
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Real-time AI moderation insights — semantic context, abuse detection, image safety, and system health.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport("json")}
            className="px-3 py-2 rounded-lg text-xs font-medium bg-gray-900 dark:bg-white dark:text-gray-900 text-white shadow-sm hover:opacity-90 transition-opacity"
          >
            Export JSON
          </button>
          <button
            onClick={() => handleExport("csv")}
            className="px-3 py-2 rounded-lg text-xs font-medium border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* ── Filters ── */}
      <DashboardFilters
        timeRange={timeRange}
        setTimeRange={setTimeRange}
        categoryFilter={categoryFilter}
        setCategoryFilter={setCategoryFilter}
      />

      {loading && (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
          Loading metrics...
        </div>
      )}

      {/* ════════════════════════════════════════════════════════
          PHASE 0: Key Outcome KPIs
          ════════════════════════════════════════════════════════ */}
      <motion.div
        variants={stagger} initial="hidden" animate="visible"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
      >
        <motion.div variants={fadeUp}><ModerationOutcome data={advancedMetrics?.outcomes} /></motion.div>
        <motion.div variants={fadeUp}><PredictionVolume data={advancedMetrics?.prediction_volume} /></motion.div>
        <motion.div variants={fadeUp}><FalsePositiveIndicator data={advancedMetrics?.false_positives} /></motion.div>
      </motion.div>

      {/* ════════════════════════════════════════════════════════
          PHASE 1 : Semantic Context & Visual Models
          ════════════════════════════════════════════════════════ */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <span className="text-[10px] uppercase tracking-widest font-bold text-indigo-500 bg-indigo-50 dark:bg-indigo-900/30 px-2.5 py-1 rounded-full">Phase 1</span>
          <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Semantic Context &amp; Visual Intelligence</h2>
        </div>
        <motion.div
          variants={stagger} initial="hidden" animate="visible"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
        >
          <motion.div variants={fadeUp} className="lg:col-span-1">
            <SemanticRelevanceGraph data={advancedMetrics?.tech_relevance} />
          </motion.div>
          <motion.div variants={fadeUp} className="lg:col-span-2">
            <ImageAnalysisMetrics data={advancedMetrics?.outcomes} />
          </motion.div>
        </motion.div>
      </div>

      {/* ════════════════════════════════════════════════════════
          PHASE 2 : Abuse & Harm Detection Models
          ════════════════════════════════════════════════════════ */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <span className="text-[10px] uppercase tracking-widest font-bold text-rose-500 bg-rose-50 dark:bg-rose-900/30 px-2.5 py-1 rounded-full">Phase 2</span>
          <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Abuse &amp; Harm Detection</h2>
        </div>
        <motion.div
          variants={stagger} initial="hidden" animate="visible"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
        >
          <motion.div variants={fadeUp} className="lg:col-span-1">
            <ToxicityBreakdownChart data={advancedMetrics?.outcomes?.top_reasons} />
          </motion.div>
          <motion.div variants={fadeUp} className="lg:col-span-1">
            <HateSpeechMetricsCard data={advancedMetrics?.outcomes} />
          </motion.div>
          <motion.div variants={fadeUp} className="lg:col-span-1">
            <ConfidenceDistribution data={advancedMetrics?.confidence_distribution} />
          </motion.div>
        </motion.div>
      </div>

      {/* ════════════════════════════════════════════════════════
          PHASE 3 : System Accuracy & Pipeline Health
          ════════════════════════════════════════════════════════ */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <span className="text-[10px] uppercase tracking-widest font-bold text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30 px-2.5 py-1 rounded-full">Phase 3</span>
          <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">System Accuracy &amp; Pipeline Health</h2>
        </div>
        <motion.div
          variants={stagger} initial="hidden" animate="visible"
          className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5"
        >
          <motion.div variants={fadeUp}>
            <ConfusionMatrix matrix={{ tn: 8452, fp: 312, fn: 287, tp: 4291 }} />
          </motion.div>
          <motion.div variants={fadeUp}>
            <ModelAgreement data={advancedMetrics?.model_agreement} />
          </motion.div>
        </motion.div>

        <motion.div
          variants={stagger} initial="hidden" animate="visible"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
        >
          <motion.div variants={fadeUp}><LatencyMetrics data={advancedMetrics?.latency} /></motion.div>
          <motion.div variants={fadeUp}><PipelineLatency data={advancedMetrics?.pipeline_latency} /></motion.div>
          <motion.div variants={fadeUp} className="space-y-5">
            <CategoryBarChart data={categoryBreakdown} />
            <SystemHealthCard health={systemHealth} />
          </motion.div>
        </motion.div>
      </div>

      {/* ════════════════════════════════════════════════════════
          PHASE 4 : Detection Signals & Edge Cases
          ════════════════════════════════════════════════════════ */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <span className="text-[10px] uppercase tracking-widest font-bold text-amber-600 bg-amber-50 dark:bg-amber-900/30 px-2.5 py-1 rounded-full">Phase 4</span>
          <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Detection Signals &amp; Edge Cases</h2>
        </div>
        <motion.div
          variants={stagger} initial="hidden" animate="visible"
          className="grid grid-cols-1 md:grid-cols-2 gap-5"
        >
          <motion.div variants={fadeUp}><TopTriggerKeywords data={advancedMetrics?.top_keywords} /></motion.div>
          <motion.div variants={fadeUp}><EdgeCaseDetector data={advancedMetrics?.edge_cases} /></motion.div>
        </motion.div>
      </div>

      {/* ════════════════════════════════════════════════════════
          Critical Flags & Recent Predictions
          ════════════════════════════════════════════════════════ */}
      <RecentCriticalFlags data={advancedMetrics?.recent_critical} />
      <RecentPredictionsTable items={filteredPredictions} />
    </div>
  );
}