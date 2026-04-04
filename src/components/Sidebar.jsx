import { Activity, LayoutDashboard, Infinity, SquarePen } from "lucide-react";
import { motion } from "framer-motion";

export default function Sidebar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: "analytics", label: "Analytics", icon: Activity },
    { id: "metrics", label: "Metrics", icon: LayoutDashboard },
    { id: "create", label: "Create Post", icon: SquarePen },
    { id: "feed", label: "Feed", icon: LayoutDashboard },
  ];

  return (
    <motion.div
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="w-64 h-screen fixed left-0 top-0 bg-white border-r border-slate-200 flex flex-col py-8 px-4 shadow-sm z-20"
    >
      {/* Logo with infinity symbol */}
      <div className="flex items-center gap-3 px-4 mb-12 group cursor-pointer">
        <motion.div
          className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-200"
          whileHover={{ rotate: 180 }}
          transition={{ type: "spring", stiffness: 200, damping: 10 }}
        >
          <Infinity className="w-6 h-6 text-white" />
        </motion.div>
        <div className="flex flex-col">
          <h1 className="text-2xl font-black tracking-tighter text-slate-900 group-hover:text-indigo-600 transition-colors">
            LOOPS
          </h1>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none">Analytics Hub</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl transition-all duration-200 group relative
                ${isActive
                  ? "bg-indigo-50 text-indigo-600"
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                }
              `}
            >
              {isActive && (
                <motion.div
                  layoutId="activeNav"
                  className="absolute inset-0 bg-indigo-50 rounded-2xl -z-10 border border-indigo-100"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <Icon
                className={`w-5 h-5 transition-transform duration-200 ${isActive ? "scale-110 stroke-[2.5px]" : "group-hover:scale-110"
                  }`}
              />
              <span className="font-bold text-sm tracking-tight">{item.label}</span>
              {isActive && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="ml-auto w-1.5 h-1.5 bg-indigo-600 rounded-full"
                />
              )}
            </button>
          );
        })}
      </nav>

      <div className="mt-auto px-2 py-4 border-t border-slate-100">
        <div className="flex items-center gap-2 text-slate-400">
          <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
          <span className="text-[10px] font-bold uppercase tracking-wider">Engine Online</span>
        </div>
      </div>
    </motion.div>
  );
}