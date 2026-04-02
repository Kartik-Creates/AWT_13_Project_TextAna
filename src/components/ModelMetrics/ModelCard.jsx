export default function ModelCard({ title, stats, extra }) {
  if (!stats) return null;

  return (
    <div className="bg-white/80 dark:bg-neutral-900/80 rounded-xl shadow-sm border border-gray-200/60 dark:border-neutral-800 p-4 sm:p-6 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {title}
        </h3>
        {extra}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
        {stats.accuracy != null && (
          <div>
            <p className="text-gray-500 dark:text-gray-400">Accuracy</p>
            <p className="font-semibold text-gray-900 dark:text-gray-100">
              {stats.accuracy.toFixed(1)}%
            </p>
          </div>
        )}
        <div>
          <p className="text-gray-500 dark:text-gray-400">Avg response</p>
          <p className="font-semibold text-gray-900 dark:text-gray-100">
            {Math.round(stats.avg_response_time_ms || 0)} ms
          </p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">Avg confidence</p>
          <p className="font-semibold text-gray-900 dark:text-gray-100">
            {(stats.avg_confidence || 0).toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-gray-500 dark:text-gray-400">Total</p>
          <p className="font-semibold text-gray-900 dark:text-gray-100">
            {stats.total_predictions || 0}
          </p>
        </div>
      </div>
    </div>
  );
}

