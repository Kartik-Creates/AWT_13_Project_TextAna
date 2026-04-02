export default function ConfusionMatrix({ matrix }) {
  if (!matrix) return null;

  const { tn, fp, fn, tp } = matrix;

  // Compute derived metrics
  const precision = tp + fp > 0 ? (tp / (tp + fp)) : 0;
  const recall = tp + fn > 0 ? (tp / (tp + fn)) : 0;
  const f1 = precision + recall > 0 ? (2 * precision * recall) / (precision + recall) : 0;
  const accuracy = tn + fp + fn + tp > 0 ? ((tn + tp) / (tn + fp + fn + tp)) : 0;

  const cells = [
    { label: "TN", value: tn, bg: "bg-emerald-50", text: "text-emerald-700", desc: "True Negative" },
    { label: "FP", value: fp, bg: "bg-amber-50", text: "text-amber-700", desc: "False Positive" },
    { label: "FN", value: fn, bg: "bg-rose-50", text: "text-rose-700", desc: "False Negative" },
    { label: "TP", value: tp, bg: "bg-blue-50", text: "text-blue-700", desc: "True Positive" },
  ];

  const metrics = [
    { label: "Precision", value: (precision * 100).toFixed(1), color: "text-blue-600", good: precision >= 0.9 },
    { label: "Recall", value: (recall * 100).toFixed(1), color: "text-violet-600", good: recall >= 0.9 },
    { label: "F1 Score", value: (f1 * 100).toFixed(1), color: "text-emerald-600", good: f1 >= 0.9 },
    { label: "Accuracy", value: (accuracy * 100).toFixed(1), color: "text-gray-700", good: accuracy >= 0.9 },
  ];

  return (
    <div className="bg-white/60 dark:bg-neutral-900/60 rounded-xl border border-gray-200/60 dark:border-neutral-800 p-5">
      <p className="font-semibold text-gray-800 dark:text-gray-100 mb-3 text-sm">
        Confusion Matrix
      </p>

      <div className="flex flex-col sm:flex-row gap-4">
        {/* Matrix grid */}
        <div className="flex-shrink-0">
          {/* Header row */}
          <div className="grid grid-cols-[60px_1fr_1fr] gap-1.5 mb-1">
            <div />
            <p className="text-[10px] text-gray-400 text-center">Pred. Neg</p>
            <p className="text-[10px] text-gray-400 text-center">Pred. Pos</p>
          </div>
          <div className="grid grid-cols-[60px_1fr_1fr] gap-1.5">
            {/* Actual Negative row */}
            <p className="text-[10px] text-gray-400 flex items-center justify-end pr-1">Act. Neg</p>
            {cells.slice(0, 2).map((c) => (
              <div key={c.label} className={`${c.bg} rounded-lg p-2.5 text-center min-w-[70px]`}>
                <p className="text-[9px] text-gray-500 mb-0.5">{c.label}</p>
                <p className={`font-bold text-sm ${c.text}`}>{c.value ?? "—"}</p>
              </div>
            ))}
            {/* Actual Positive row */}
            <p className="text-[10px] text-gray-400 flex items-center justify-end pr-1">Act. Pos</p>
            {cells.slice(2).map((c) => (
              <div key={c.label} className={`${c.bg} rounded-lg p-2.5 text-center min-w-[70px]`}>
                <p className="text-[9px] text-gray-500 mb-0.5">{c.label}</p>
                <p className={`font-bold text-sm ${c.text}`}>{c.value ?? "—"}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Derived metrics */}
        <div className="flex-1 grid grid-cols-2 gap-2">
          {metrics.map((m) => (
            <div
              key={m.label}
              className={`rounded-lg p-2.5 text-center border ${
                m.good ? "border-emerald-200 bg-emerald-50/50" : "border-gray-100 bg-gray-50/50"
              }`}
            >
              <p className="text-[10px] text-gray-500 mb-0.5">{m.label}</p>
              <p className={`font-bold text-base ${m.color}`}>{m.value}%</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
