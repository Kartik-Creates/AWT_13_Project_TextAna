export default function ConfusionMatrix({ matrix }) {
  if (!matrix) return null;

  const { tn, fp, fn, tp } = matrix;

  // Compute derived metrics
  const precision = tp + fp > 0 ? (tp / (tp + fp)) : 0;
  const recall = tp + fn > 0 ? (tp / (tp + fn)) : 0;
  const f1 = precision + recall > 0 ? (2 * precision * recall) / (precision + recall) : 0;
  const accuracy = tn + fp + fn + tp > 0 ? ((tn + tp) / (tn + fp + fn + tp)) : 0;

  const cells = [
    { label: "TN", value: tn, bg: "bg-gradient-to-br from-teal-50 to-emerald-100 dark:from-teal-900/50 dark:to-emerald-800/50 border border-teal-200/50 dark:border-teal-700/50 hover:shadow-[0_0_15px_rgba(20,184,166,0.3)]", text: "text-teal-800 dark:text-teal-200", desc: "True Negative" },
    { label: "FP", value: fp, bg: "bg-gradient-to-br from-orange-50 to-red-100 dark:from-orange-900/50 dark:to-red-800/50 border border-orange-200/50 dark:border-orange-700/50 hover:shadow-[0_0_15px_rgba(249,115,22,0.3)]", text: "text-orange-800 dark:text-orange-200", desc: "False Positive" },
    { label: "FN", value: fn, bg: "bg-gradient-to-br from-pink-50 to-rose-100 dark:from-pink-900/50 dark:to-rose-800/50 border border-pink-200/50 dark:border-pink-700/50 hover:shadow-[0_0_15px_rgba(236,72,153,0.3)]", text: "text-pink-800 dark:text-pink-200", desc: "False Negative" },
    { label: "TP", value: tp, bg: "bg-gradient-to-br from-indigo-50 to-purple-100 dark:from-indigo-900/50 dark:to-purple-800/50 border border-indigo-200/50 dark:border-indigo-700/50 hover:shadow-[0_0_15px_rgba(99,102,241,0.3)]", text: "text-indigo-800 dark:text-indigo-200", desc: "True Positive" },
  ];

  const metrics = [
    { label: "Precision", value: (precision * 100).toFixed(1), color: "text-blue-600 dark:text-blue-400", glow: "hover:shadow-[0_0_15px_rgba(59,130,246,0.4)] hover:border-blue-400/50" },
    { label: "Recall", value: (recall * 100).toFixed(1), color: "text-violet-600 dark:text-violet-400", glow: "hover:shadow-[0_0_15px_rgba(139,92,246,0.4)] hover:border-violet-400/50" },
    { label: "F1 Score", value: (f1 * 100).toFixed(1), color: "text-emerald-600 dark:text-emerald-400", glow: "hover:shadow-[0_0_15px_rgba(16,185,129,0.4)] hover:border-emerald-400/50" },
    { label: "Accuracy", value: (accuracy * 100).toFixed(1), color: "text-sky-600 dark:text-sky-400", glow: "hover:shadow-[0_0_15px_rgba(14,165,233,0.4)] hover:border-sky-400/50" },
  ];

  return (
    <div className="bg-gradient-to-br from-white/70 to-white/30 dark:from-slate-900/80 dark:to-slate-900/40 backdrop-blur-xl rounded-[20px] border border-white/50 dark:border-slate-700/50 shadow-lg hover:shadow-2xl hover:scale-[1.03] transition-all duration-300 ease-in-out p-5 h-full">
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
              <div key={c.label} className={`${c.bg} rounded-xl p-2.5 text-center min-w-[70px] hover:scale-[1.05] transition-all duration-300 ease-in-out`}>
                <p className="text-[9px] text-gray-500 dark:text-gray-400 mb-0.5">{c.label}</p>
                <p className={`font-bold text-sm ${c.text}`}>{c.value ?? "—"}</p>
              </div>
            ))}
            {/* Actual Positive row */}
            <p className="text-[10px] text-gray-400 flex items-center justify-end pr-1">Act. Pos</p>
            {cells.slice(2).map((c) => (
              <div key={c.label} className={`${c.bg} rounded-xl p-2.5 text-center min-w-[70px] hover:scale-[1.05] transition-all duration-300 ease-in-out`}>
                <p className="text-[9px] text-gray-500 dark:text-gray-400 mb-0.5">{c.label}</p>
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
              className={`rounded-xl p-2.5 text-center backdrop-blur-md bg-white/40 dark:bg-neutral-800/40 border border-white/50 dark:border-white/10 hover:scale-[1.03] transition-all duration-300 ease-in-out ${m.glow}`}
            >
              <p className="text-[10px] text-gray-500 dark:text-gray-400 mb-0.5">{m.label}</p>
              <p className={`font-bold text-base ${m.color}`}>{m.value}%</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
