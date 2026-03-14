import { motion } from "framer-motion";
import { BarChart3, ShieldCheck, ShieldAlert, Layers } from "lucide-react";

export default function AnalyticsPage() {
  const stats = [
    {
      label: "Total Posts",
      value: "12,450",
      icon: Layers,
      color: "text-blue-500",
      bg: "bg-blue-50",
      trend: "+12.5%",
    },
    {
      label: "Allowed Posts",
      value: "11,820",
      icon: ShieldCheck,
      color: "text-emerald-500",
      bg: "bg-emerald-50",
      trend: "+14.2%",
    },
    {
      label: "Blocked Posts",
      value: "630",
      icon: ShieldAlert,
      color: "text-rose-500",
      bg: "bg-rose-50",
      trend: "-2.4%",
    },
  ];

  return (
    <div className="p-8 max-w-6xl mx-auto w-full">
      <div className="mb-10 flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 tracking-tight">Platform Analytics</h2>
          <p className="text-gray-500 mt-2 text-sm">Real-time overview of content moderation</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow-sm border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
          <BarChart3 className="w-4 h-4" />
          <span className="hidden sm:inline">Detailed Report</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1, duration: 0.4 }}
              className="glass-panel p-6 rounded-2xl relative overflow-hidden group hover:shadow-lg transition-all"
            >
              {/* Decorative gradient blob */}
              <div className={`absolute -right-6 -top-6 w-24 h-24 rounded-full ${stat.bg} opacity-50 group-hover:scale-150 transition-transform duration-500 ease-out`} />
              
              <div className="relative z-10 flex justify-between items-start mb-4">
                <div className={`p-3 rounded-xl ${stat.bg}`}>
                  <Icon className={`w-6 h-6 ${stat.color}`} />
                </div>
                <div className={`text-xs font-semibold px-2 py-1 rounded-full ${stat.trend.startsWith('+') ? 'text-emerald-700 bg-emerald-100' : 'text-rose-700 bg-rose-100'}`}>
                  {stat.trend}
                </div>
              </div>
              
              <div className="relative z-10">
                <h3 className="text-gray-500 text-sm font-medium">{stat.label}</h3>
                <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
              </div>
            </motion.div>
          );
        })}
      </div>

      <div className="mt-8 glass-panel rounded-2xl p-8 flex items-center justify-center min-h-[300px] border border-gray-100">
        <div className="text-center text-gray-400 flex flex-col items-center">
          <BarChart3 className="w-12 h-12 mb-3 opacity-20" />
          <p>Detailed charts will appear here</p>
        </div>
      </div>
    </div>
  );
}
