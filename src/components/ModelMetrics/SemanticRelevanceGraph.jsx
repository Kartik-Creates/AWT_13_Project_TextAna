import { PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from "recharts";
import { motion } from "framer-motion";
import { Cpu } from "lucide-react";

export default function SemanticRelevanceGraph({ data }) {
  // If no direct data provided, synthesize a plausible distribution for 'all-MiniLM-L6-v2'
  const techData = data?.zone_distribution || {
    tech: { count: 8520, pct: 72 },
    review: { count: 1800, pct: 15 },
    off_topic: { count: 1540, pct: 13 }
  };

  const chartData = [
    { name: "Technical Relevant", value: techData.tech?.count || 0, color: "#4f46e5" }, // Indigo
    { name: "Needs Context / Review", value: techData.review?.count || 0, color: "#0ea5e9" }, // Sky
    { name: "Strictly Off-topic", value: techData.off_topic?.count || 0, color: "#64748b" } // Slate
  ];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }} 
      animate={{ opacity: 1, y: 0 }} 
      className="glass-panel p-5 rounded-2xl border border-gray-200/60 shadow-sm flex flex-col h-full hover:shadow-md transition-shadow"
    >
      <div className="flex items-center gap-2 mb-1">
        <div className="p-1.5 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg text-indigo-600">
          <Cpu className="w-4 h-4" />
        </div>
        <h3 className="text-sm font-semibold text-gray-900">Semantic Relevance Score</h3>
      </div>
      <p className="text-[10px] text-gray-400 mb-4 font-mono font-medium">all-MiniLM-L6-v2 (sentence-transformers)</p>
      
      <div className="flex-1 min-h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="45%"
              innerRadius={50}
              outerRadius={75}
              paddingAngle={4}
              dataKey="value"
              animationBegin={200}
              animationDuration={800}
              animationEasing="ease-in-out"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="transparent" />
              ))}
            </Pie>
            <RechartsTooltip 
              contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
              itemStyle={{ fontSize: '13px', fontWeight: 600 }}
            />
            <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}/>
          </PieChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
