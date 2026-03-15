export default function TimeSeriesChart() {
  // Placeholder sparkline-style chart – real time-series can be added later.
  const points = [78, 80, 82, 79, 83, 85, 84, 86];

  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;

  return (
    <div className="bg-white/80 dark:bg-neutral-900/80 rounded-xl shadow-sm border border-gray-200/60 dark:border-neutral-800 p-4 sm:p-6">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
        Category trends (sample)
      </h3>
      <svg viewBox="0 0 100 30" className="w-full h-16 text-emerald-400">
        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          points={points
            .map((p, i) => {
              const x = (i / (points.length - 1)) * 100;
              const y = 30 - ((p - min) / range) * 24 - 3;
              return `${x},${y}`;
            })
            .join(" ")}
        />
      </svg>
      <p className="mt-1 text-[11px] text-gray-500 dark:text-gray-400">
        Sample time-series illustration. Hook into a real metrics endpoint
        when historical data is available.
      </p>
    </div>
  );
}

