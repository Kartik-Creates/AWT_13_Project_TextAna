import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { motion } from "framer-motion";
import { ShieldAlert } from "lucide-react";

export default function ToxicityBreakdownChart({ data }) {
  // Use real backend reasons if provided, otherwise mock the unitary/toxic-bert logic
  const mockData = [
    { category: "Toxic", value: 85, color: "#f43f5e" },       // Rose
    { category: "Severe", value: 45, color: "#e11d48" },      // Rose deeper
    { category: "Threat", value: 12, color: "#9f1239" },      // Dark red
    { category: "Obscene", value: 65, color: "#fb923c" },     // Orange
    { category: "Insult", value: 72, color: "#f59e0b" },      // Amber
    { category: "Identity Hate", value: 24, color: "#b91c1c"} // Red
  ];

  const processedData = data ? data.map(item => ({
    category: item.reason,
    value: item.count,
    color: "#f43f5e" 
  })) : mockData;

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.98 }} 
      animate={{ opacity: 1, scale: 1 }} 
      transition={{ delay: 0.1 }}
      className="glass-panel p-5 rounded-2xl border border-gray-200/60 shadow-sm flex flex-col h-full hover:shadow-md transition-shadow"
    >
      <div className="flex items-center gap-2 mb-1">
        <div className="p-1.5 bg-rose-100 dark:bg-rose-900/30 rounded-lg text-rose-600">
          <ShieldAlert className="w-4 h-4" />
        </div>
        <h3 className="text-sm font-semibold text-gray-900">Toxicity Analysis Breakdown</h3>
      </div>
      <p className="text-[10px] text-gray-400 mb-5 font-mono font-medium">unitary/toxic-bert (multi-label)</p>

      <div className="flex-1 min-h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={processedData} layout="vertical" margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
            <XAxis type="number" hide />
            <YAxis dataKey="category" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b', fontWeight: 500 }} width={90}/>
            <Tooltip 
              cursor={{ fill: 'rgba(0,0,0,0.02)' }}
              contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={16}>
              {processedData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color || '#f43f5e'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
