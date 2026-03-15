export default function RecentPredictionsTable({ items }) {
  if (!items || items.length === 0) return null;

  return (
    <div className="bg-white/80 dark:bg-neutral-900/80 rounded-xl shadow-sm border border-gray-200/60 dark:border-neutral-800 p-4 sm:p-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          Recent predictions
        </h3>
        <span className="text-[11px] text-gray-500 dark:text-gray-400">
          Last {items.length}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead>
            <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-neutral-800">
              <th className="py-1 pr-4">ID</th>
              <th className="py-1 pr-4">Text / Input</th>
              <th className="py-1 pr-4">Model</th>
              <th className="py-1 pr-4">Decision</th>
              <th className="py-1 pr-4 text-right">Time</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => {
              const preview =
                item.input_preview && item.input_preview !== "[image]"
                  ? item.input_preview.slice(0, 40)
                  : item.input_type === "image"
                  ? "[image]"
                  : "[pair]";

              let decision = "-";
              if (item.input_type === "text") {
                decision = item.category || "safe";
              } else if (item.input_type === "image") {
                decision = item.category || "nsfw";
              } else if (item.input_type === "pair") {
                decision = item.category || "mismatch";
              }

              return (
                <tr
                  key={item._id || idx}
                  className="border-b border-gray-50 dark:border-neutral-800/80"
                >
                  <td className="py-1 pr-4 text-gray-500 dark:text-gray-400">
                    {idx + 1}
                  </td>
                  <td className="py-1 pr-4 text-gray-800 dark:text-gray-100">
                    {preview}
                  </td>
                  <td className="py-1 pr-4 text-gray-700 dark:text-gray-200 capitalize">
                    {item.model}
                  </td>
                  <td className="py-1 pr-4 text-gray-700 dark:text-gray-200 capitalize">
                    {decision}
                  </td>
                  <td className="py-1 pr-4 text-gray-600 dark:text-gray-300 text-right">
                    {Math.round(item.response_time_ms || 0)} ms
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

