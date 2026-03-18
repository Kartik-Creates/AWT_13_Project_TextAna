import { Users } from "lucide-react";

export default function ModelAgreement({ data }) {
  const agreement = data || { agreement_pct: 0, total_posts: 0, agreed: 0 };
  const pct = agreement.agreement_pct || 0;

  const color =
    pct >= 90 ? "text-emerald-600" : pct >= 70 ? "text-amber-600" : "text-rose-600";
  const bg =
    pct >= 90 ? "bg-emerald-50" : pct >= 70 ? "bg-amber-50" : "bg-rose-50";
  const ring =
    pct >= 90
      ? "stroke-emerald-500"
      : pct >= 70
      ? "stroke-amber-500"
      : "stroke-rose-500";

  const circumference = 2 * Math.PI * 36;
  const dashOffset = circumference - (pct / 100) * circumference;

  return (
    <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
      <div className="flex items-center gap-2 mb-3">
        <div className={`p-1.5 rounded-lg ${bg}`}>
          <Users className={`w-3.5 h-3.5 ${color}`} />
        </div>
        <h3 className="text-sm font-semibold text-gray-900">Model Agreement</h3>
      </div>

      <div className="flex items-center gap-4">
        {/* Ring gauge */}
        <div className="relative w-20 h-20 flex-shrink-0">
          <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
            <circle
              cx="40" cy="40" r="36"
              fill="none" stroke="#e5e7eb" strokeWidth="6"
            />
            <circle
              cx="40" cy="40" r="36"
              fill="none"
              className={ring}
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              style={{ transition: "stroke-dashoffset 0.6s ease" }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-base font-bold ${color}`}>{pct}%</span>
          </div>
        </div>

        <div className="text-xs text-gray-500 space-y-1">
          <p>
            <span className="font-medium text-gray-700">{agreement.agreed}</span> of{" "}
            <span className="font-medium text-gray-700">{agreement.total_posts}</span> posts
          </p>
          <p>All models agreed on classification</p>
        </div>
      </div>
    </div>
  );
}
