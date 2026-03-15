export default function LanguagePieChart({ data }) {
  if (!data || !data.items || data.items.length === 0) return null;

  const total = data.total || 0;

  return (
    <div className="bg-white/80 dark:bg-neutral-900/80 rounded-xl shadow-sm border border-gray-200/60 dark:border-neutral-800 p-4 sm:p-6">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
        Language distribution
      </h3>
      <div className="flex items-center gap-4">
        <div className="relative w-28 h-28">
          <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-indigo-500 to-emerald-400 opacity-70" />
          <div className="absolute inset-3 rounded-full bg-white dark:bg-neutral-900" />
          <div className="absolute inset-6 flex items-center justify-center">
            <span className="text-xs text-gray-600 dark:text-gray-300 text-center">
              {total} texts
            </span>
          </div>
        </div>
        <div className="flex-1 space-y-1 text-xs">
          {data.items.map((item) => (
            <div
              key={item.language}
              className="flex items-center justify-between gap-2"
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-gradient-to-r from-sky-500 to-indigo-500" />
                <span className="capitalize text-gray-700 dark:text-gray-200">
                  {item.language}
                </span>
              </div>
              <span className="text-gray-500 dark:text-gray-400">
                {item.percentage.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

