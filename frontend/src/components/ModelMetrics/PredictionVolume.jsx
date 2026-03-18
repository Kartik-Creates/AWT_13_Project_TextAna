import { Activity, TrendingUp, Zap } from "lucide-react";

export default function PredictionVolume({ data }) {
  const volume = data || { last_1h: 0, last_24h: 0, peak_per_hour: 0 };

  const cards = [
    { label: "Last 1 Hour", value: volume.last_1h, icon: Activity, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Last 24 Hours", value: volume.last_24h, icon: TrendingUp, color: "text-violet-600", bg: "bg-violet-50" },
    { label: "Peak / Hour", value: volume.peak_per_hour, icon: Zap, color: "text-amber-600", bg: "bg-amber-50" },
  ];

  return (
    <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Prediction Volume</h3>
      <div className="grid grid-cols-3 gap-3">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.label} className="text-center">
              <div className={`inline-flex p-2 rounded-lg ${c.bg} mb-2`}>
                <Icon className={`w-4 h-4 ${c.color}`} />
              </div>
              <p className="text-xl font-bold text-gray-900">{c.value}</p>
              <p className="text-[11px] text-gray-500 mt-0.5">{c.label}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
