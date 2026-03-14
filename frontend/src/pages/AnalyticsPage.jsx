import { motion } from "framer-motion";
import { BarChart3, ShieldCheck, ShieldAlert, Layers } from "lucide-react";
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from "recharts";

// Mock data representing the last 7 days of moderation activity
const moderationData = [
  { date: "Mon", allowed: 1200, blocked: 45 },
  { date: "Tue", allowed: 1350, blocked: 52 },
  { date: "Wed", allowed: 1420, blocked: 68 },
  { date: "Thu", allowed: 1380, blocked: 50 },
  { date: "Fri", allowed: 1650, blocked: 85 },
  { date: "Sat", allowed: 1850, blocked: 120 },
  { date: "Sun", allowed: 2100, blocked: 156 },
];

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
    <div className="p-8 max-w-6xl mx-auto w-full pb-20">
      <div className="mb-10 flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 tracking-tight">Platform Analytics</h2>
          <p className="text-gray-500 mt-2 text-sm">Real-time overview of content moderation</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow-sm border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
          <BarChart3 className="w-4 h-4" />
          <span className="hidden sm:inline">Export Report</span>
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
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

      {/* Interactive Chart Section */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5 }}
        className="glass-panel rounded-2xl p-6 border border-gray-100 mb-8 overflow-hidden relative"
      >
        <div className="mb-6 flex justify-between items-end relative z-10">
          <div>
            <h3 className="text-xl font-bold text-gray-900">Moderation Activity</h3>
            <p className="text-sm text-gray-500">Allowed vs Blocked posts over the last 7 days</p>
          </div>
          <div className="flex gap-4 text-sm font-medium">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-emerald-500"></span>
              <span className="text-gray-600">Allowed</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-500"></span>
              <span className="text-gray-600">Blocked</span>
            </div>
          </div>
        </div>

        {/* The Recharts AreaChart */}
        <div className="h-[350px] w-full relative z-10">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={moderationData}
              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorAllowed" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorBlocked" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis 
                dataKey="date" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: '#64748b', fontSize: 13 }}
                dy={10}
              />
              <YAxis 
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: '#64748b', fontSize: 13 }}
                dx={-10}
              />
              <Tooltip 
                contentStyle={{ 
                  borderRadius: '12px', 
                  border: 'none', 
                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                  backgroundColor: 'rgba(255, 255, 255, 0.95)',
                  backdropFilter: 'blur(8px)'
                }}
                itemStyle={{ fontWeight: '500' }}
              />
              <Area 
                type="monotone" 
                dataKey="allowed" 
                name="Allowed Posts"
                stroke="#10b981" 
                strokeWidth={3}
                fillOpacity={1} 
                fill="url(#colorAllowed)" 
                activeDot={{ r: 6, strokeWidth: 0 }}
              />
              <Area 
                type="monotone" 
                dataKey="blocked" 
                name="Blocked Posts"
                stroke="#ef4444" 
                strokeWidth={3}
                fillOpacity={1} 
                fill="url(#colorBlocked)" 
                activeDot={{ r: 6, strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </motion.div>
    </div>
  );
}
