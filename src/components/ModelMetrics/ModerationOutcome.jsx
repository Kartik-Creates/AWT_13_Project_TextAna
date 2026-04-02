import { ShieldCheck, ShieldAlert } from "lucide-react";

export default function ModerationOutcome({ data }) {
  const outcomes = data || {};
  const total = outcomes.total || 0;
  const allowed = outcomes.allowed || 0;
  const blocked = outcomes.blocked || 0;
  const allowedPct = outcomes.allowed_pct || 0;
  const blockedPct = outcomes.blocked_pct || 0;
  const reasons = outcomes.top_reasons || [];

  return (
    <div className="bg-white/80 rounded-xl shadow-sm border border-gray-200/60 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Moderation Outcomes</h3>

      {/* Allowed / Blocked summary */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-emerald-50 rounded-lg p-3 text-center">
          <ShieldCheck className="w-5 h-5 text-emerald-600 mx-auto mb-1" />
          <p className="text-xl font-bold text-emerald-700">{allowed}</p>
          <p className="text-[11px] text-emerald-600 font-medium">{allowedPct}% Allowed</p>
        </div>
        <div className="bg-rose-50 rounded-lg p-3 text-center">
          <ShieldAlert className="w-5 h-5 text-rose-600 mx-auto mb-1" />
          <p className="text-xl font-bold text-rose-700">{blocked}</p>
          <p className="text-[11px] text-rose-600 font-medium">{blockedPct}% Blocked</p>
        </div>
      </div>

      {/* Stacked progress bar */}
      {total > 0 && (
        <div className="h-2.5 w-full rounded-full bg-gray-100 overflow-hidden flex mb-4">
          <div
            className="h-full bg-emerald-500 transition-all"
            style={{ width: `${allowedPct}%` }}
          />
          <div
            className="h-full bg-rose-500 transition-all"
            style={{ width: `${blockedPct}%` }}
          />
        </div>
      )}

      {/* Top block reasons */}
      {reasons.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-700 mb-2">Top Block Reasons</p>
          <div className="space-y-1.5">
            {reasons.slice(0, 5).map((r) => {
              const max = reasons[0]?.count || 1;
              const pct = (r.count / max) * 100;
              return (
                <div key={r.reason} className="space-y-0.5">
                  <div className="flex justify-between text-xs">
                    <span className="capitalize text-gray-600">{r.reason}</span>
                    <span className="text-gray-400">{r.count} ({r.percentage}%)</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-rose-400 to-orange-400"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
