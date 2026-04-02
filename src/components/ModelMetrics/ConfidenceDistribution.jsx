import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip } from "recharts";

export default function ConfidenceDistribution({ data }) {
  const buckets = data || { low: 0, medium: 0, high: 0 };
  const total = buckets.low + buckets.medium + buckets.high;

  const chartData = [
    { label: "< 0.7", value: buckets.low, color: "#ef4444", labelFull: "Low (< 0.7)" },
    { label: "0.7–0.9", value: buckets.medium, color: "#f59e0b", labelFull: "Medium (0.7–0.9)" },
    { label: "0.9–1.0", value: buckets.high, color: "#10b981", labelFull: "High (0.9–1.0)" },
  ];

  return (
    <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Confidence Distribution</h3>

      {total === 0 ? (
        <p className="text-xs text-gray-400">No confidence data yet</p>
      ) : (
        <>
          <div className="h-[140px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <XAxis
                  dataKey="label"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#64748b", fontSize: 11 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#94a3b8", fontSize: 10 }}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: "10px",
                    border: "none",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                    fontSize: "12px",
                  }}
                  formatter={(value, name, props) => [
                    `${value} predictions (${total ? ((value / total) * 100).toFixed(1) : 0}%)`,
                    props.payload.labelFull,
                  ]}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={50}>
                  {chartData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.color} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div className="flex justify-center gap-4 mt-2 text-[11px]">
            {chartData.map((d) => (
              <div key={d.label} className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                <span className="text-gray-500">
                  {d.labelFull}: {d.value}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
