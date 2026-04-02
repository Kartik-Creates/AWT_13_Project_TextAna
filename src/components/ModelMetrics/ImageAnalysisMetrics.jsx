import { motion } from "framer-motion";
import { Image as ImageIcon, EyeOff } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

export default function ImageAnalysisMetrics({ data }) {
  // NSFW mock data mapping to ViT-based model
  const nsfwTotal = data?.top_reasons?.find(r => r.reason === 'nsfw')?.count || 89;
  const safeImage = 3450; // Mock base count for images isolated
  
  const pieData = [
    { name: "Safe", value: safeImage, color: "#10b981" },
    { name: "NSFW", value: nsfwTotal, color: "#f43f5e" }
  ];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }} 
      animate={{ opacity: 1, y: 0 }} 
      transition={{ delay: 0.3 }}
      className="glass-panel p-5 rounded-2xl border border-gray-200/60 shadow-sm flex flex-col h-full hover:shadow-md transition-shadow relative overflow-hidden"
    >
      <div className="flex items-center gap-2 mb-1">
        <div className="p-1.5 bg-fuchsia-100 dark:bg-fuchsia-900/30 rounded-lg text-fuchsia-600">
          <ImageIcon className="w-4 h-4" />
        </div>
        <h3 className="text-sm font-semibold text-gray-900">Visual Model Analysis</h3>
      </div>
      <p className="text-[10px] text-gray-400 mb-6 font-mono font-medium">CLIP (ViT-B/32) & NSFW (ViT)</p>

      <div className="grid grid-cols-2 gap-4 flex-1">
        
        {/* Left Block: CLIP */}
        <div className="flex flex-col items-center justify-center p-3 rounded-xl border border-gray-100 bg-gray-50/50">
          <p className="text-[11px] text-gray-500 font-semibold mb-2">CLIP Tech Relevance</p>
          <div className="relative w-20 h-20 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90">
              <circle cx="40" cy="40" r="34" stroke="currentColor" strokeWidth="6" fill="transparent" className="text-gray-200" />
              <circle cx="40" cy="40" r="34" stroke="currentColor" strokeWidth="6" fill="transparent" strokeDasharray="213" strokeDashoffset="42" className="text-indigo-500" strokeLinecap="round" />
            </svg>
            <span className="absolute text-sm font-bold text-gray-800">80%</span>
          </div>
          <p className="text-[10px] text-gray-400 mt-2 text-center">Avg Embedding Cosine</p>
        </div>

        {/* Right Block: NSFW */}
        <div className="flex flex-col items-center justify-center p-3 rounded-xl border border-gray-100 bg-gray-50/50">
          <p className="text-[11px] text-gray-500 font-semibold mb-2">NSFW Classifier</p>
          <div className="w-20 h-20 relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={22} outerRadius={34} paddingAngle={2} dataKey="value" stroke="none">
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <EyeOff className="w-4 h-4 text-gray-400" />
            </div>
          </div>
          <p className="text-[10px] text-rose-500 mt-2 text-center font-medium bg-rose-50 px-2 py-0.5 rounded-full">{nsfwTotal} Blocked</p>
        </div>

      </div>
    </motion.div>
  );
}
