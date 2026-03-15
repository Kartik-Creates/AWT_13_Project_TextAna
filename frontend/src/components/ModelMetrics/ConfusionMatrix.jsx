export default function ConfusionMatrix({ matrix }) {
  if (!matrix) return null;

  const { tn, fp, fn, tp } = matrix;

  return (
    <div className="bg-white/60 dark:bg-neutral-900/60 rounded-lg border border-gray-200/60 dark:border-neutral-800 p-4 text-xs">
      <p className="font-semibold text-gray-800 dark:text-gray-100 mb-2">
        Confusion Matrix (last window)
      </p>
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-emerald-50 dark:bg-emerald-900/40 rounded-md p-2">
          <p className="text-[10px] text-gray-500 dark:text-gray-400">TN</p>
          <p className="font-semibold text-emerald-700 dark:text-emerald-300">
            {tn ?? "-"}
          </p>
        </div>
        <div className="bg-amber-50 dark:bg-amber-900/40 rounded-md p-2">
          <p className="text-[10px] text-gray-500 dark:text-gray-400">FP</p>
          <p className="font-semibold text-amber-700 dark:text-amber-300">
            {fp ?? "-"}
          </p>
        </div>
        <div className="bg-rose-50 dark:bg-rose-900/40 rounded-md p-2">
          <p className="text-[10px] text-gray-500 dark:text-gray-400">FN</p>
          <p className="font-semibold text-rose-700 dark:text-rose-300">
            {fn ?? "-"}
          </p>
        </div>
        <div className="bg-blue-50 dark:bg-blue-900/40 rounded-md p-2">
          <p className="text-[10px] text-gray-500 dark:text-gray-400">TP</p>
          <p className="font-semibold text-blue-700 dark:text-blue-300">
            {tp ?? "-"}
          </p>
        </div>
      </div>
    </div>
  );
}

