import { useEffect, useState, useCallback } from "react";
import ModelCard from "./ModelCard";
import ConfusionMatrix from "./ConfusionMatrix";
import LanguagePieChart from "./LanguagePieChart";
import CategoryBarChart from "./CategoryBarChart";
import RecentPredictionsTable from "./RecentPredictionsTable";
import SystemHealthCard from "./SystemHealthCard";
import TimeSeriesChart from "./TimeSeriesChart";

const POLL_INTERVAL_MS = 30000;

export default function ModelMetricsDashboard() {
  const [modelMetrics, setModelMetrics] = useState(null);
  const [languageDistribution, setLanguageDistribution] = useState(null);
  const [categoryBreakdown, setCategoryBreakdown] = useState(null);
  const [recentPredictions, setRecentPredictions] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [modelsRes, langRes, catRes, recentRes, healthRes] =
        await Promise.all([
          fetch("/api/metrics/models"),
          fetch("/api/metrics/language-distribution"),
          fetch("/api/metrics/category-breakdown"),
          fetch("/api/metrics/recent-predictions?limit=10"),
          fetch("/api/metrics/system-health"),
        ]);

      if (modelsRes.ok) {
        setModelMetrics(await modelsRes.json());
      }
      if (langRes.ok) {
        setLanguageDistribution(await langRes.json());
      }
      if (catRes.ok) {
        setCategoryBreakdown(await catRes.json());
      }
      if (recentRes.ok) {
        setRecentPredictions(await recentRes.json());
      }
      if (healthRes.ok) {
        setSystemHealth(await healthRes.json());
      }
    } catch (err) {
      console.error("Failed to load metrics dashboard data", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchAll]);

  const robertaStats = modelMetrics?.roberta;
  const efficientnetStats = modelMetrics?.efficientnet;
  const clipStats = modelMetrics?.clip;

  const handleExport = async (format = "json") => {
    const payload = {
      modelMetrics,
      languageDistribution,
      categoryBreakdown,
      recentPredictions,
      systemHealth,
    };

    if (format === "json") {
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "model-metrics.json";
      a.click();
      URL.revokeObjectURL(url);
    } else if (format === "csv") {
      // Minimal CSV export for recent predictions
      const header = "id,model,input_type,category,response_time_ms\n";
      const rows =
        recentPredictions
          ?.map((p, idx) => {
            const cat = p.category || "";
            return `${idx + 1},${p.model},${p.input_type},${cat},${
              p.response_time_ms || ""
            }`;
          })
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
            Model Performance Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Real-time view of toxicity, NSFW, and relevance models across your
            moderation pipeline.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport("json")}
            className="px-3 py-2 rounded-lg text-xs font-medium bg-gray-900 text-white dark:bg-white dark:text-gray-900 shadow-sm hover:opacity-90"
          >
            Export JSON
          </button>
          <button
            onClick={() => handleExport("csv")}
            className="px-3 py-2 rounded-lg text-xs font-medium border border-gray-300 dark:border-neutral-700 text-gray-700 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-neutral-800"
          >
            Export CSV
          </button>
        </div>
      </div>

      {loading && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Loading metrics...
        </p>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-4">
          <ModelCard
            title="Text Toxicity (XLM-RoBERTa)"
            stats={robertaStats}
            extra={
              <span className="text-[11px] text-gray-500 dark:text-gray-400">
                multilingual-toxic-xlm-roberta
              </span>
            }
          />
          <ConfusionMatrix
            matrix={{
              tn: 8452,
              fp: 312,
              fn: 287,
              tp: 4291,
            }}
          />
        </div>
        <div className="space-y-4">
          <ModelCard
            title="NSFW Detection (EfficientNet)"
            stats={efficientnetStats}
          />
          <ModelCard title="Image-Text Relevance (CLIP)" stats={clipStats} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="space-y-4 lg:col-span-2">
          <CategoryBarChart data={categoryBreakdown} />
          <TimeSeriesChart />
        </div>
        <div className="space-y-4">
          <LanguagePieChart data={languageDistribution} />
          <SystemHealthCard health={systemHealth} />
        </div>
      </div>

      <RecentPredictionsTable items={recentPredictions} />
    </div>
  );
}

