import { AlertTriangle, ShieldAlert } from "lucide-react";

export default function RecentCriticalFlags({ data }) {
  const items = data || [];

  if (items.length === 0) {
    return (
      <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Recent Critical Flags</h3>
        <div className="text-center py-4">
          <ShieldAlert className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-xs text-gray-400">No critical flags in this period</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-4 h-4 text-rose-500" />
        <h3 className="text-sm font-semibold text-gray-900">Recent Critical Flags</h3>
        <span className="ml-auto text-[11px] font-medium text-rose-500 bg-rose-50 px-2 py-0.5 rounded-full">
          {items.length} flagged
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-100">
              <th className="py-1.5 pr-3">Content</th>
              <th className="py-1.5 pr-3">Category</th>
              <th className="py-1.5 pr-3">Severity</th>
              <th className="py-1.5 pr-3">Model</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => {
              const preview =
                item.input_preview && item.input_preview !== "[image]"
                  ? item.input_preview.slice(0, 50) + (item.input_preview.length > 50 ? "…" : "")
                  : "[image]";

              const severityColor =
                item.severity === "high"
                  ? "text-rose-700 bg-rose-50"
                  : "text-amber-700 bg-amber-50";

              return (
                <tr
                  key={item._id || idx}
                  className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors"
                >
                  <td className="py-2 pr-3 text-gray-800 max-w-[200px] truncate">
                    {preview}
                  </td>
                  <td className="py-2 pr-3">
                    <span className="capitalize text-gray-700 font-medium">{item.category}</span>
                  </td>
                  <td className="py-2 pr-3">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold capitalize ${severityColor}`}>
                      {item.severity}
                    </span>
                  </td>
                  <td className="py-2 pr-3 capitalize text-gray-500">{item.model}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
