import { Gauge, Zap, Timer } from "lucide-react";

export default function LatencyMetrics({ data }) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Latency Metrics</h3>
        <p className="text-xs text-gray-400">No latency data yet</p>
      </div>
    );
  }

  // Aggregate across all models
  const allP95 = [];
  const allP99 = [];
  const allMax = [];
  Object.values(data).forEach((m) => {
    if (m.p95) allP95.push(m.p95);
    if (m.p99) allP99.push(m.p99);
    if (m.max) allMax.push(m.max);
  });

  const cards = [
    {
      label: "P95 Latency",
      value: allP95.length ? `${Math.round(Math.max(...allP95))} ms` : "—",
      icon: Timer,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
    {
      label: "P99 Latency",
      value: allP99.length ? `${Math.round(Math.max(...allP99))} ms` : "—",
      icon: Gauge,
      color: "text-amber-600",
      bg: "bg-amber-50",
    },
    {
      label: "Max Latency",
      value: allMax.length ? `${Math.round(Math.max(...allMax))} ms` : "—",
      icon: Zap,
      color: "text-rose-600",
      bg: "bg-rose-50",
    },
  ];

  return (
    <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Latency Metrics</h3>
      <div className="grid grid-cols-3 gap-3">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.label} className="text-center">
              <div className={`inline-flex p-2 rounded-lg ${c.bg} mb-2`}>
                <Icon className={`w-4 h-4 ${c.color}`} />
              </div>
              <p className="text-lg font-bold text-gray-900">{c.value}</p>
              <p className="text-[11px] text-gray-500 mt-0.5">{c.label}</p>
            </div>
          );
        })}
      </div>

      {/* Per-model breakdown */}
      <div className="mt-4 pt-3 border-t border-gray-100 space-y-2">
        {Object.entries(data).map(([model, m]) => (
          <div key={model} className="flex items-center justify-between text-xs">
            <span className="capitalize text-gray-600 font-medium">{model}</span>
            <span className="text-gray-400">
              P95: {m.p95}ms · P99: {m.p99}ms · Max: {m.max}ms
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
