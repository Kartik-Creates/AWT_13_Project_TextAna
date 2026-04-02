export default function CategoryBarChart({ data }) {
  if (!data || !data.items || data.items.length === 0) return null;

  const max = Math.max(...data.items.map((i) => i.count || 0), 1);

  return (
    <div className="bg-white/80 dark:bg-neutral-900/80 rounded-xl shadow-sm border border-gray-200/60 dark:border-neutral-800 p-4 sm:p-6">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
        Content categories
      </h3>
      <div className="space-y-2">
        {data.items.map((item) => {
          const pct = ((item.count || 0) / max) * 100;
          return (
            <div key={item.category} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="capitalize text-gray-700 dark:text-gray-200">
                  {item.category}
                </span>
                <span className="text-gray-500 dark:text-gray-400">
                  {item.count || 0} (
                  {item.percentage ? item.percentage.toFixed(1) : "0.0"}%)
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-neutral-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-sky-500"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

