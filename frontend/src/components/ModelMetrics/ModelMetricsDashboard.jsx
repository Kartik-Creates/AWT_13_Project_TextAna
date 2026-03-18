import { useEffect, useState, useCallback } from "react";

// Existing (updated) components
import ModelCard from "./ModelCard";
import ConfusionMatrix from "./ConfusionMatrix";
import CategoryBarChart from "./CategoryBarChart";
import RecentPredictionsTable from "./RecentPredictionsTable";
import SystemHealthCard from "./SystemHealthCard";

// New components
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
      const [modelsRes, catRes, recentRes, healthRes, advancedRes] =
        await Promise.all([
          fetch("/api/metrics/models"),
          fetch("/api/metrics/category-breakdown"),
          fetch("/api/metrics/recent-predictions?limit=10"),
          fetch("/api/metrics/system-health"),
          fetch(`/api/metrics/advanced?hours=${Math.ceil(timeRange)}`),
        ]);

      if (modelsRes.ok) setModelMetrics(await modelsRes.json());
      if (catRes.ok) setCategoryBreakdown(await catRes.json());
      if (recentRes.ok) setRecentPredictions(await recentRes.json());
      if (healthRes.ok) setSystemHealth(await healthRes.json());
      if (advancedRes.ok) setAdvancedMetrics(await advancedRes.json());
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

  const robertaStats = modelMetrics?.roberta;
  const efficientnetStats = modelMetrics?.efficientnet;
  const clipStats = modelMetrics?.clip;

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-gray-900">
            Moderation Analytics
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Real-time AI moderation insights — system health, model accuracy, and content risk analysis.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport("json")}
            className="px-3 py-2 rounded-lg text-xs font-medium bg-gray-900 text-white shadow-sm hover:opacity-90"
          >
            Export JSON
          </button>
          <button
            onClick={() => handleExport("csv")}
            className="px-3 py-2 rounded-lg text-xs font-medium border border-gray-300 text-gray-700 hover:bg-gray-50"
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Filters */}
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

      {/* ═══════════════════════════════════════════════
          Row 1: Key Outcome Metrics
          ═══════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <ModerationOutcome data={advancedMetrics?.outcomes} />
        <PredictionVolume data={advancedMetrics?.prediction_volume} />
        <FalsePositiveIndicator data={advancedMetrics?.false_positives} />
      </div>

      {/* ═══════════════════════════════════════════════
          Row 2: Performance & Latency
          ═══════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <LatencyMetrics data={advancedMetrics?.latency} />
        <PipelineLatency data={advancedMetrics?.pipeline_latency} />
        <ConfidenceDistribution data={advancedMetrics?.confidence_distribution} />
      </div>

      {/* ═══════════════════════════════════════════════
          Row 3: Model Cards + Confusion Matrix
          ═══════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-4">
          <ModelCard
            title="Text Toxicity (XLM-RoBERTa)"
            stats={robertaStats}
            extra={
              <span className="text-[11px] text-gray-500">
                multilingual-toxic-xlm-roberta
              </span>
            }
          />
          <ConfusionMatrix
            matrix={{ tn: 8452, fp: 312, fn: 287, tp: 4291 }}
          />
        </div>
        <div className="space-y-4">
          <ModelCard title="NSFW Detection (EfficientNet)" stats={efficientnetStats} />
          <ModelCard title="Image-Text Relevance (CLIP)" stats={clipStats} />
          <ModelAgreement data={advancedMetrics?.model_agreement} />
        </div>
      </div>

      {/* ═══════════════════════════════════════════════
          Row 4: Detection & Patterns
          ═══════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <TopTriggerKeywords data={advancedMetrics?.top_keywords} />
        <EdgeCaseDetector data={advancedMetrics?.edge_cases} />
        <div className="space-y-4">
          <CategoryBarChart data={categoryBreakdown} />
          <SystemHealthCard health={systemHealth} />
        </div>
      </div>

      {/* ═══════════════════════════════════════════════
          Row 5: Critical Flags + Recent Predictions
          ═══════════════════════════════════════════════ */}
      <RecentCriticalFlags data={advancedMetrics?.recent_critical} />
      <RecentPredictionsTable items={filteredPredictions} />
    </div>
  );
}
