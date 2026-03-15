export default function SystemHealthCard({ health }) {
  if (!health) return null;

  const statusColor =
    health.api_status === "operational" ? "text-emerald-500" : "text-amber-500";

  return (
    <div className="bg-white/80 dark:bg-neutral-900/80 rounded-xl shadow-sm border border-gray-200/60 dark:border-neutral-800 p-4 sm:p-6">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
        System health
      </h3>
      <div className="space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-gray-500 dark:text-gray-400">API Status</span>
          <span className={`font-semibold ${statusColor}`}>Operational</span>
        </div>
        <div className="border-t border-gray-100 dark:border-neutral-800 my-2" />
        <div className="flex items-center justify-between">
          <span className="text-gray-500 dark:text-gray-400">Models</span>
          <span className="text-emerald-500 text-[11px]">
            RoBERTa • EfficientNet • CLIP
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-500 dark:text-gray-400">Queue size</span>
          <span className="text-gray-800 dark:text-gray-100">
            {health.queue_size ?? 0}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-500 dark:text-gray-400">Avg response</span>
          <span className="text-gray-800 dark:text-gray-100">
            {health.avg_response_time_ms != null
              ? `${Math.round(health.avg_response_time_ms)} ms`
              : "—"}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-500 dark:text-gray-400">Uptime</span>
          <span className="text-gray-800 dark:text-gray-100">
            {health.uptime || "—"}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-500 dark:text-gray-400">Total predictions</span>
          <span className="text-gray-800 dark:text-gray-100">
            {health.total_predictions ?? 0}
          </span>
        </div>
      </div>
    </div>
  );
}

