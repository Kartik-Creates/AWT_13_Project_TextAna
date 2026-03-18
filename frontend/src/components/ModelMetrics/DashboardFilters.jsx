import { Clock, Filter } from "lucide-react";

const TIME_RANGES = [
  { label: "10 min", hours: 0.167 },
  { label: "1 hour", hours: 1 },
  { label: "24 hours", hours: 24 },
  { label: "7 days", hours: 168 },
];

const CATEGORY_FILTERS = [
  { label: "All", value: "all" },
  { label: "Blocked", value: "blocked" },
  { label: "Spam", value: "spam" },
  { label: "NSFW", value: "nsfw" },
  { label: "High Severity", value: "high" },
];

export default function DashboardFilters({ timeRange, setTimeRange, categoryFilter, setCategoryFilter }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Time range */}
      <div className="flex items-center gap-1.5 bg-white/80 rounded-xl border border-gray-200/60 p-1 shadow-sm">
        <Clock className="w-3.5 h-3.5 text-gray-400 ml-2" />
        {TIME_RANGES.map((t) => (
          <button
            key={t.hours}
            onClick={() => setTimeRange(t.hours)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              timeRange === t.hours
                ? "bg-gray-900 text-white shadow-sm"
                : "text-gray-500 hover:text-gray-800 hover:bg-gray-100"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Category filters */}
      <div className="flex items-center gap-1.5 bg-white/80 rounded-xl border border-gray-200/60 p-1 shadow-sm">
        <Filter className="w-3.5 h-3.5 text-gray-400 ml-2" />
        {CATEGORY_FILTERS.map((c) => (
          <button
            key={c.value}
            onClick={() => setCategoryFilter(c.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              categoryFilter === c.value
                ? "bg-gray-900 text-white shadow-sm"
                : "text-gray-500 hover:text-gray-800 hover:bg-gray-100"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>
    </div>
  );
}
