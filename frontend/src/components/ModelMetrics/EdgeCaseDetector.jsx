import { AlertCircle, Type, Link } from "lucide-react";

export default function EdgeCaseDetector({ data }) {
  const edge = data || { short_text: 0, empty_input: 0, url_only: 0 };
  const total = edge.short_text + edge.empty_input + edge.url_only;

  const items = [
    {
      label: "Short Text (< 5 words)",
      count: edge.short_text,
      icon: Type,
      color: "text-amber-600",
      bg: "bg-amber-50",
    },
    {
      label: "Empty Inputs",
      count: edge.empty_input,
      icon: AlertCircle,
      color: "text-rose-600",
      bg: "bg-rose-50",
    },
    {
      label: "URL-Only Inputs",
      count: edge.url_only,
      icon: Link,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
  ];

  return (
    <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900">Edge Case Detector</h3>
        <span className="text-[11px] text-gray-400 font-medium">{total} total</span>
      </div>
      <div className="space-y-2.5">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className={`p-1.5 rounded-md ${item.bg}`}>
                  <Icon className={`w-3.5 h-3.5 ${item.color}`} />
                </div>
                <span className="text-xs text-gray-600">{item.label}</span>
              </div>
              <span className={`text-sm font-bold ${item.count > 0 ? item.color : "text-gray-400"}`}>
                {item.count}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
