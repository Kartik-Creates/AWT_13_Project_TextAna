import { motion } from "framer-motion";
import { AlertOctagon, ShieldCheck } from "lucide-react";

export default function HateSpeechMetricsCard({ data }) {
  // Extract hate speech blocking stats
  const totalHateSpeech = data?.top_reasons?.find(r => r.reason === 'hate_speech')?.count || 124;
  const safeContent = data?.allowed || 8452;
  const total = totalHateSpeech + safeContent;
  const safePct = ((safeContent / total) * 100).toFixed(1);
  const hatePct = ((totalHateSpeech / total) * 100).toFixed(1);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }} 
      animate={{ opacity: 1, y: 0 }} 
      transition={{ delay: 0.2 }}
      className="glass-panel p-5 rounded-2xl border border-gray-200/60 shadow-sm flex flex-col h-full hover:shadow-md transition-shadow relative overflow-hidden"
    >
      {/* Decorative background element */}
      <div className="absolute right-0 top-0 w-32 h-32 bg-gradient-to-bl from-rose-500/10 to-transparent rounded-bl-full pointer-events-none" />

      <div className="flex items-center gap-2 mb-1 z-10">
        <div className="p-1.5 bg-rose-50 dark:bg-rose-900/30 rounded-lg text-rose-500">
          <AlertOctagon className="w-4 h-4" />
        </div>
        <h3 className="text-sm font-semibold text-gray-900">Hate Speech Detection</h3>
      </div>
      <p className="text-[10px] text-gray-400 mb-6 font-mono font-medium z-10">dehatebert-mono-english</p>

      <div className="flex flex-col flex-1 justify-center gap-6 z-10">
        {/* KPI 1 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs text-gray-400 font-medium tracking-wide uppercase">Safe Pattern</p>
              <p className="text-xl font-bold text-gray-900">{safeContent}</p>
            </div>
          </div>
          <span className="text-emerald-500 font-bold">{safePct}%</span>
        </div>

        {/* Custom Progress Bar */}
        <div className="w-full h-2 rounded-full bg-rose-100 overflow-hidden flex">
          <div className="h-full bg-emerald-400" style={{ width: `${safePct}%` }} />
          <div className="h-full bg-rose-500" style={{ width: `${hatePct}%` }} />
        </div>

        {/* KPI 2 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-rose-100 flex items-center justify-center text-rose-600">
              <AlertOctagon className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs text-gray-400 font-medium tracking-wide uppercase">Flagged Hate</p>
              <p className="text-xl font-bold text-gray-900">{totalHateSpeech}</p>
            </div>
          </div>
          <span className="text-rose-500 font-bold">{hatePct}%</span>
        </div>
      </div>
    </motion.div>
  );
}
