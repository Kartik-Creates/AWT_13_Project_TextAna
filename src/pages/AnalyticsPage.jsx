import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart as RePieChart, Pie, Cell, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  Treemap, Sankey
} from "recharts";
import postService from "../services/postService";

const COLORS = {
  allowed: "#10b981", // Green
  blocked: "#ef4444", // Red
  total: "#3b82f6",   // Blue
  pie: ["#3b82f6", "#8b5cf6", "#f59e0b", "#ec4899", "#10b981", "#6366f1", "#f43f5e"]
};

// Minimal Animated Chart Wrapper
const ChartBox = ({ title, children, delay = 0 }) => (
  <motion.div 
    initial={{ opacity: 0, y: 15 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5, delay, ease: "easeOut" }}
    whileHover={{ y: -2 }}
    className="flex flex-col h-full w-full bg-white/40 dark:bg-white/5 backdrop-blur-sm p-4 border border-gray-100/50 dark:border-white/10 rounded-2xl overflow-hidden shadow-sm shadow-slate-100 dark:shadow-none hover:shadow-md dark:hover:shadow-none hover:border-gray-200/60 dark:hover:border-white/20 transition-all duration-300 group"
  >
    <div className="flex items-center justify-between mb-2">
      <h3 className="text-[10px] font-black text-gray-400 dark:text-gray-500 uppercase tracking-[0.2em] group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors">{title}</h3>
      <div className="w-1 h-1 rounded-full bg-indigo-500/20 group-hover:bg-indigo-500/60 transition-colors" />
    </div>
    <div className="flex-1 w-full min-h-0">
      {children}
    </div>
  </motion.div>
);

// Interactive Stat Card
const StatCard = ({ label, value, color }) => (
  <motion.div 
    whileHover={{ y: -4, scale: 1.02 }}
    transition={{ type: "spring", stiffness: 400, damping: 12 }}
    className="bg-white/50 dark:bg-white/10 backdrop-blur-sm border border-gray-100/50 dark:border-white/10 p-3 px-5 rounded-2xl shadow-sm shadow-slate-100 dark:shadow-none w-fit min-w-[130px] cursor-pointer group"
  >
    <p className="text-[9px] font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest">{label}</p>
    <p className="text-xl font-black mt-0.5 transition-colors group-hover:drop-shadow-sm" style={{ color }}>{value}</p>
  </motion.div>
);

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white/95 dark:bg-slate-900 backdrop-blur-md p-3 rounded-xl shadow-xl border border-gray-100 dark:border-white/10 text-[11px] font-medium transition-all">
        <p className="text-gray-900 dark:text-white mb-2 font-black border-b border-gray-50 dark:border-white/10 pb-1">{label}</p>
        <div className="space-y-1">
          {payload.map((entry, index) => (
            <div key={index} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: entry.color }} />
                {entry.name}
              </span>
              <span className="font-bold text-gray-900 dark:text-white">{entry.value}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

const TreemapContent = (props) => {
  const { x, y, width, height, index, name } = props;
  return (
    <g>
      <rect
        x={x} y={y} width={width} height={height}
        fill={COLORS.pie[index % COLORS.pie.length]}
        stroke="#ffffff" strokeWidth="2"
        rx="6" ry="6"
        className="opacity-90 hover:opacity-100 transition-opacity duration-300"
        style={{ cursor: 'pointer' }}
      />
      {width > 40 && height > 20 && (
        <text 
          x={x + width / 2} y={y + height / 2 + 4} 
          textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="bold"
          className="pointer-events-none drop-shadow-md"
        >
          {name}
        </text>
      )}
    </g>
  );
};

const SankeyNode = (props) => {
  const { x, y, width, height, index, payload } = props;
  const isLeft = x < 100;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={COLORS.pie[index % COLORS.pie.length]} rx="3" ry="3" className="drop-shadow-sm" />
      <text 
        x={isLeft ? x + width + 6 : x - 6} 
        y={y + height / 2 + 3} 
        textAnchor={isLeft ? "start" : "end"} 
        fill="#94a3b8" 
        fontSize="10" 
        fontWeight="black" 
        className="pointer-events-none drop-shadow-sm"
      >
        {payload.name}
      </text>
    </g>
  );
};

const SankeyLink = (props) => {
  const { sourceX, targetX, sourceY, targetY, sourceControlX, targetControlX, linkWidth, index } = props;
  return (
    <path
      d={`M${sourceX},${sourceY} C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}`}
      fill="none" stroke={`url(#sankeyGrad${index % 3})`} strokeWidth={Math.max(2, linkWidth)} strokeOpacity="0.5"
      className="hover:stroke-opacity-100 transition-all duration-300 cursor-pointer"
    />
  );
};

export default function AnalyticsPage() {
  const [allPosts, setAllPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAllPosts = async () => {
      try {
        const data = await postService.getFeed(1, 500);
        if (Array.isArray(data)) {
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

    // Flow Data (Sankey)
    const flowData = {
      nodes: [{ name: "Input" }, { name: "AI Check" }, { name: "Allowed" }, { name: "Blocked" }, { name: "Review" }],
      links: [
        { source: 0, target: 1, value: Math.max(1, summaryMetrics.total) },
        { source: 1, target: 2, value: Math.max(1, summaryMetrics.allowed) },
        { source: 1, target: 3, value: Math.max(1, summaryMetrics.blocked) },
        { source: 1, target: 4, value: Math.max(1, Math.floor(summaryMetrics.total * 0.05)) }
      ]
    };

    // Category Data (Treemap)
    const categoryData = [
      { name: 'Safe', size: Math.max(1, summaryMetrics.allowed) },
      { name: 'Spam', size: Math.max(1, Math.floor(summaryMetrics.blocked * 0.4)) },
      { name: 'Abuse', size: Math.max(1, Math.floor(summaryMetrics.blocked * 0.3)) },
      { name: 'Sensitive', size: Math.max(1, Math.floor(summaryMetrics.blocked * 0.3)) }
    ];

    return { overviewData, bannedWordsData, trendingTopicsData, activityData, topics, flowData, categoryData };
  }, [allPosts, summaryMetrics]);

  if (loading && !allPosts.length) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400 dark:text-gray-500 font-medium bg-gray-50/50 dark:bg-slate-900/50">
        Initializing Insight Flow...
      </div>
    );
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: "easeOut" }}
      className="flex flex-col min-h-[500px] h-[calc(100vh-6rem)] w-full max-w-[1800px] mx-auto overflow-hidden px-4 md:px-6 lg:px-8 py-3 gap-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 shrink-0">
        <div>
          <h1 className="text-lg font-black text-slate-900 dark:text-white tracking-tighter">ANALYTICS ENGINE</h1>
          <p className="text-[9px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest leading-none mt-1">Real-time content flow</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 border border-emerald-100 dark:bg-emerald-900/30 dark:border-emerald-800 rounded-full">
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

      {/* 3x2 Grid */}
      <div className="grid grid-cols-3 grid-rows-2 gap-3 flex-1 min-h-0 pb-1 relative">
        <svg width="0" height="0" className="absolute">
          <defs>
            <linearGradient id="sankeyGrad0" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#8b5cf6" />
            </linearGradient>
            <linearGradient id="sankeyGrad1" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#8b5cf6" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
            <linearGradient id="sankeyGrad2" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#f59e0b" />
              <stop offset="100%" stopColor="#ef4444" />
            </linearGradient>
          </defs>
        </svg>

        <ChartBox title="Posts Overview" delay={0.1}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={processedData?.overviewData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 'bold' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 'bold' }} />
              <Tooltip cursor={{ fill: '#f8fafc' }} content={<CustomTooltip />} />
              <Bar dataKey="Allowed" fill={COLORS.allowed} radius={[2, 2, 0, 0]} barSize={8} animationDuration={600} animationEasing="ease-in-out" />
              <Bar dataKey="Pending/Blocked" fill={COLORS.blocked} radius={[2, 2, 0, 0]} barSize={8} animationDuration={600} animationEasing="ease-in-out" />
              <Bar dataKey="Total" fill={COLORS.total} radius={[2, 2, 0, 0]} barSize={8} animationDuration={600} animationEasing="ease-in-out" />
            </BarChart>
          </ResponsiveContainer>
        </ChartBox>

        <ChartBox title="Content Flow Analysis" delay={0.2}>
          <ResponsiveContainer width="100%" height="100%">
            <Sankey
              data={processedData?.flowData}
              node={<SankeyNode />}
              link={<SankeyLink />}
              margin={{ top: 15, right: 35, left: 15, bottom: 15 }}
            >
              <Tooltip content={<CustomTooltip />} />
            </Sankey>
          </ResponsiveContainer>
        </ChartBox>

        <ChartBox title="Content Category Breakdown" delay={0.3}>
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={processedData?.categoryData}
              dataKey="size"
              aspectRatio={4 / 3}
              stroke="#fff"
              content={<TreemapContent />}
              animationDuration={800}
              animationEasing="ease-in-out"
            >
              <Tooltip content={<CustomTooltip />} />
            </Treemap>
          </ResponsiveContainer>
        </ChartBox>

        <ChartBox title="Banned Words %" delay={0.4}>
          <ResponsiveContainer width="100%" height="100%">
            <RePieChart>
              <Pie
                data={processedData?.bannedWordsData?.length ? processedData.bannedWordsData : [{ name: 'Safe', value: 1 }]}
                cx="50%" cy="50%" innerRadius="55%" outerRadius="80%" paddingAngle={4}
                dataKey="value" animationDuration={800} animationEasing="ease-in-out" labelLine={false}
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

        <ChartBox title="Trending Topics" delay={0.5}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={processedData?.trendingTopicsData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 'bold' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 'bold' }} />
              <Tooltip content={<CustomTooltip />} />
              {processedData?.topics?.map((word, idx) => (
                <Line key={word} type="monotone" dataKey={word} stroke={COLORS.pie[idx % COLORS.pie.length]} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 0 }} animationDuration={1000} animationEasing="ease-in-out" />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </ChartBox>

        <ChartBox title="Hourly flow Volume" delay={0.6}>
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
              <Area type="monotone" dataKey="Activity" stroke={COLORS.total} strokeWidth={3} fillOpacity={1} fill="url(#areaGrad)" activeDot={{ r: 6, strokeWidth: 0 }} animationDuration={1000} animationEasing="ease-in-out" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartBox>
      </div>

    </motion.div>
  );
}