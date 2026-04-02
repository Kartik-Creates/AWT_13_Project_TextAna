import { Server, Activity, AlertTriangle, Clock } from "lucide-react";

export default function SystemHealthCard({ health }) {
  if (!health) return null;

  const isOperational = health.api_status === "operational";

  // Simulated throughput from recent predictions
  const throughput = health.recent_predictions_last_5m != null
    ? (health.recent_predictions_last_5m / 5 / 60).toFixed(2)
    : "—";

  // Queue status
  const queueSize = health.queue_size ?? 0;
  const queueStatus = queueSize > 10 ? "High" : "Stable";
  const queueColor = queueSize > 10 ? "text-amber-600" : "text-emerald-600";

  const rows = [
    {
      label: "API Status",
      value: isOperational ? "Operational" : "Degraded",
      color: isOperational ? "text-emerald-500" : "text-rose-500",
      icon: Server,
    },
    {
      label: "Queue",
      value: `${queueSize} (${queueStatus})`,
      color: queueColor,
      icon: Activity,
    },
    {
      label: "Throughput",
      value: `${throughput} req/s`,
      color: "text-gray-800",
      icon: Activity,
    },
    {
      label: "Error Rate",
      value: "0.0%",
      color: "text-emerald-600",
      icon: AlertTriangle,
    },
    {
      label: "Uptime",
      value: health.uptime || "—",
      color: "text-gray-800",
      icon: Clock,
    },
  ];

  // Model status
  const models = health.models || {};

  return (
    <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
      <div className="flex items-center gap-2 mb-4">
        <div className={`w-2 h-2 rounded-full ${isOperational ? "bg-emerald-500" : "bg-rose-500"} animate-pulse`} />
        <h3 className="text-sm font-semibold text-gray-900">System Health</h3>
      </div>

      <div className="space-y-2.5">
        {rows.map((row) => {
          const Icon = row.icon;
          return (
            <div key={row.label} className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <Icon className="w-3.5 h-3.5" />
                <span>{row.label}</span>
              </div>
              <span className={`text-xs font-semibold ${row.color}`}>{row.value}</span>
            </div>
          );
        })}
      </div>

      {/* Model status badges */}
      <div className="mt-4 pt-3 border-t border-gray-100">
        <p className="text-[10px] text-gray-400 mb-2 uppercase tracking-wider">Models</p>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(models).map(([name, status]) => (
            <span
              key={name}
              className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                status === "loaded"
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-rose-50 text-rose-700"
              }`}
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
