export default function TopTriggerKeywords({ data }) {
  const keywords = data || [];

  if (keywords.length === 0) {
    return (
      <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Top Trigger Keywords</h3>
        <p className="text-xs text-gray-400">No triggered keywords yet</p>
      </div>
    );
  }

  const maxCount = keywords[0]?.count || 1;

  return (
    <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Top Trigger Keywords</h3>
      <div className="space-y-2">
        {keywords.slice(0, 8).map((kw, idx) => {
          const pct = (kw.count / maxCount) * 100;
          return (
            <div key={kw.keyword} className="space-y-0.5">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-gray-400 w-4 text-right">{idx + 1}.</span>
                  <span className="capitalize text-gray-700 font-medium">{kw.keyword}</span>
                </div>
                <span className="text-gray-500 font-medium">{kw.count}</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-gray-100 overflow-hidden ml-6">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-violet-400 to-indigo-500"
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
