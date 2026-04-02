import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from "recharts";

const MODEL_COLORS = {
  roberta: "#6366f1",
  efficientnet: "#f59e0b",
  clip: "#10b981",
};

const MODEL_LABELS = {
  roberta: "Text (RoBERTa)",
  efficientnet: "Image (EfficientNet)",
  clip: "Relevance (CLIP)",
};

export default function PipelineLatency({ data }) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Pipeline Latency Breakdown</h3>
        <p className="text-xs text-gray-400">No latency data yet</p>
      </div>
    );
  }

  const chartData = Object.entries(data).map(([model, avg]) => ({
    model: MODEL_LABELS[model] || model,
    avg: Math.round(avg),
    color: MODEL_COLORS[model] || "#94a3b8",
  }));

  const totalMs = chartData.reduce((sum, d) => sum + d.avg, 0);

  return (
    <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-900">Pipeline Latency Breakdown</h3>
        <span className="text-xs text-gray-400">Total: {totalMs} ms</span>
      </div>

      <div className="h-[120px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
            <XAxis
              type="number"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#94a3b8", fontSize: 10 }}
              unit=" ms"
            />
            <YAxis
              type="category"
              dataKey="model"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#64748b", fontSize: 11 }}
              width={120}
            />
            <Tooltip
              contentStyle={{
                borderRadius: "10px",
                border: "none",
                boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                fontSize: "12px",
              }}
              formatter={(value) => [`${value} ms`, "Avg Response Time"]}
            />
            <Bar dataKey="avg" radius={[0, 6, 6, 0]} maxBarSize={24}>
              {chartData.map((entry, idx) => (
                <Cell key={idx} fill={entry.color} fillOpacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
