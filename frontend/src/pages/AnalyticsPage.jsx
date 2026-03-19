import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart as RePieChart, Pie, Cell, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";

const COLORS = {
  allowed: "#10b981", // Green
  blocked: "#ef4444", // Red
  total: "#3b82f6",   // Blue
  pie: ["#3b82f6", "#8b5cf6", "#f59e0b", "#ec4899", "#10b981", "#6366f1", "#f43f5e"]
};

// Minimal Chart Wrapper
const ChartBox = ({ title, children }) => (
  <div className="flex flex-col h-full w-full bg-white/40 backdrop-blur-sm p-4 border border-gray-100/50 rounded-2xl overflow-hidden shadow-sm shadow-slate-100">
    <div className="flex items-center justify-between mb-2">
      <h3 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">{title}</h3>
      <div className="w-1 h-1 rounded-full bg-indigo-500/10" />
    </div>
    <div className="flex-1 w-full min-h-0">
      {children}
    </div>
  </div>
);

// Interactive Stat Card
const StatCard = ({ label, value, color }) => (
  <motion.div 
    whileHover={{ y: -4, scale: 1.02 }}
    transition={{ type: "spring", stiffness: 400, damping: 12 }}
    className="bg-white/50 backdrop-blur-sm border border-gray-100/50 p-3 px-5 rounded-2xl shadow-sm shadow-slate-100 w-fit min-w-[130px] cursor-pointer group"
  >
    <p className="text-[9px] font-black text-gray-400 uppercase tracking-widest">{label}</p>
    <p className="text-xl font-black mt-0.5 transition-colors group-hover:drop-shadow-sm" style={{ color }}>{value}</p>
  </motion.div>
);

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white/95 backdrop-blur-md p-3 rounded-xl shadow-xl border border-gray-100 text-[11px] font-medium transition-all">
        <p className="text-gray-900 mb-2 font-black border-b border-gray-50 pb-1">{label}</p>
        <div className="space-y-1">
          {payload.map((entry, index) => (
            <div key={index} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-1.5 text-gray-500">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: entry.color }} />
                {entry.name}
              </span>
              <span className="font-bold text-gray-900">{entry.value}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export default function AnalyticsPage() {
  const [allPosts, setAllPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAllPosts = async () => {
      try {
        const response = await fetch("/api/posts/");
        if (response.ok) {
          const data = await response.json();
          setAllPosts(data);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAllPosts();
    const interval = setInterval(fetchAllPosts, 30000);
    return () => clearInterval(interval);
  }, []);

  // Summary Metrics
  const summaryMetrics = useMemo(() => ({
    allowed: allPosts.filter(p => p.allowed === true).length,
    blocked: allPosts.filter(p => p.allowed === false).length,
    total: allPosts.length
  }), [allPosts]);

  // Chart Data Processing
  const processedData = useMemo(() => {
    if (!allPosts.length) return null;

    const dates = [...new Set(allPosts.map(p => p.created_at?.split('T')[0]).filter(Boolean))].sort().slice(-7);
    
    // Bar Chart
    const overviewData = dates.map(date => {
      const dayPosts = allPosts.filter(p => p.created_at?.startsWith(date));
      return {
        date: new Date(date).toLocaleDateString([], { month: 'short', day: 'numeric' }),
        Allowed: dayPosts.filter(p => p.allowed === true).length,
        Total: dayPosts.length,
        'Pending/Blocked': dayPosts.filter(p => p.allowed !== true).length
      };
    });

    // Pie Chart
    const bannedWordsMap = {};
    allPosts.forEach(p => {
      if (p.allowed === false && p.reasons) {
        p.reasons.forEach(word => {
          bannedWordsMap[word] = (bannedWordsMap[word] || 0) + 1;
        });
      }
    });
    const bannedWordsData = Object.entries(bannedWordsMap)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value).slice(0, 5);

    // Line Chart
    const topics = ['Safety', 'AI', 'Global', 'Future'];
    const trendingTopicsData = dates.map(date => {
      const dayPosts = allPosts.filter(p => p.created_at?.startsWith(date));
      const entry = { date: new Date(date).toLocaleDateString([], { weekday: 'short' }) };
      topics.forEach(word => {
         entry[word] = dayPosts.filter(p => p.text?.toLowerCase().includes(word.toLowerCase())).length;
      });
      return entry;
    });

    // Area Chart
    const activityData = Array.from({ length: 24 }, (_, i) => {
      const d = new Date();
      d.setHours(d.getHours() - i, 0, 0, 0);
      const hourPosts = allPosts.filter(p => {
        if (!p.created_at) return false;
        const pDate = new Date(p.created_at);
        pDate.setMinutes(0, 0, 0);
        return pDate.getTime() === d.getTime();
      });
      return {
        time: d.getHours() % 6 === 0 ? d.toLocaleString([], { hour: 'numeric' }) : '',
        Activity: hourPosts.length,
        fullTime: d.toLocaleString([], { hour: 'numeric', minute: '2-digit' })
      };
    }).reverse();

    return { overviewData, bannedWordsData, trendingTopicsData, activityData, topics };
  }, [allPosts]);

  if (loading && !allPosts.length) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400 font-medium bg-gray-50/50">
        Initializing Insight Flow...
      </div>
    );
  }

  return (
    <motion.div 
      initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="flex flex-col h-[calc(100vh-4.5rem)] w-full max-w-[1500px] mx-auto overflow-hidden p-2 gap-3"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 shrink-0">
        <div>
          <h1 className="text-xl font-black text-slate-900 tracking-tighter">ANALYTICS ENGINE</h1>
          <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest leading-none mt-1">Real-time content flow</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 rounded-full border border-emerald-100">
           <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
           <span className="text-[9px] font-black text-emerald-700 uppercase tracking-widest">Active Monitoring</span>
        </div>
      </div>

      {/* Summary Stat Cards Row */}
      <div className="flex gap-3 shrink-0">
        <StatCard label="Allowed Total" value={summaryMetrics.allowed} color={COLORS.allowed} />
        <StatCard label="Block Total" value={summaryMetrics.blocked} color={COLORS.blocked} />
        <StatCard label="All Total" value={summaryMetrics.total} color={COLORS.total} />
      </div>

      {/* 2x2 Grid */}
      <div className="grid grid-cols-2 grid-rows-2 gap-3 flex-1 min-h-0 pb-1">
        <ChartBox title="Posts Overview">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={processedData?.overviewData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 'bold' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 'bold' }} />
              <Tooltip cursor={{ fill: '#f8fafc' }} content={<CustomTooltip />} />
              <Bar dataKey="Allowed" fill={COLORS.allowed} radius={[2, 2, 0, 0]} barSize={8} />
              <Bar dataKey="Pending/Blocked" fill={COLORS.blocked} radius={[2, 2, 0, 0]} barSize={8} />
              <Bar dataKey="Total" fill={COLORS.total} radius={[2, 2, 0, 0]} barSize={8} />
            </BarChart>
          </ResponsiveContainer>
        </ChartBox>

        <ChartBox title="Banned Words %">
          <ResponsiveContainer width="100%" height="100%">
            <RePieChart>
              <Pie
                data={processedData?.bannedWordsData?.length ? processedData.bannedWordsData : [{ name: 'Safe', value: 1 }]}
                cx="50%" cy="50%" innerRadius="55%" outerRadius="80%" paddingAngle={4}
                dataKey="value" animationDuration={1000} labelLine={false}
                label={({ percent }) => percent > 0.1 ? `${(percent * 100).toFixed(0)}%` : ''}
              >
                {(processedData?.bannedWordsData?.length ? processedData.bannedWordsData : [{ name: 'Safe', value: 1 }]).map((entry, index) => (
                  <Cell key={index} fill={COLORS.pie[index % COLORS.pie.length]} stroke="#fff" strokeWidth={2} className="cursor-pointer hover:opacity-80 outline-none" />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="bottom" height={20} iconType="circle" wrapperStyle={{ fontSize: '8px', fontWeight: 'black', textTransform: 'uppercase' }} />
            </RePieChart>
          </ResponsiveContainer>
        </ChartBox>

        <ChartBox title="Trending Topics">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={processedData?.trendingTopicsData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 'bold' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 'bold' }} />
              <Tooltip content={<CustomTooltip />} />
              {processedData?.topics?.map((word, idx) => (
                <Line key={word} type="monotone" dataKey={word} stroke={COLORS.pie[idx % COLORS.pie.length]} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 0 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </ChartBox>

        <ChartBox title="Hourly flow Volume">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={processedData?.activityData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.total} stopOpacity={0.2}/><stop offset="95%" stopColor={COLORS.total} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 'bold' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 'bold' }} />
              <Tooltip labelKey="fullTime" content={<CustomTooltip />} />
              <Area type="monotone" dataKey="Activity" stroke={COLORS.total} strokeWidth={3} fillOpacity={1} fill="url(#areaGrad)" activeDot={{ r: 6, strokeWidth: 0 }} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartBox>
      </div>

    </motion.div>
  );
}