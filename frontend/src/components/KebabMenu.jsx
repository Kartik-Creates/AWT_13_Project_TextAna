import { useState, useRef, useEffect } from "react";
import { Activity, LayoutDashboard, Infinity, Moon, Sun, MoreVertical, ShieldAlert } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useTheme } from "../context/ThemeContext";

export default function KebabMenu({ activeTab, setActiveTab }) {
  const { theme, toggleTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  const navItems = [
    { id: "analytics", label: "Analytics", icon: Activity },
    { id: "metrics", label: "Metrics", icon: LayoutDashboard },
    { id: "moderation", label: "Moderation", icon: ShieldAlert },
    { id: "feed", label: "Feed", icon: LayoutDashboard },
  ];

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close on ESC
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") setIsOpen(false);
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleTabClick = (id) => {
    setActiveTab(id);
    setIsOpen(false);
  };

  return (
    <div className="fixed top-4 right-4 z-50 sm:top-6 sm:right-6" ref={menuRef}>
      {/* Trigger Button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center 
          bg-white/80 dark:bg-[#15152a]/80 backdrop-blur-md 
          border border-slate-200 dark:border-white/[0.07] 
          shadow-sm text-slate-700 dark:text-slate-300
          hover:bg-indigo-50 dark:hover:bg-indigo-500/15
          transition-colors"
        aria-label="Menu"
      >
        <MoreVertical className="w-5 h-5 sm:w-6 sm:h-6" />
      </motion.button>

      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -10, transformOrigin: "top right" }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="absolute right-0 top-14 sm:top-16 w-64 md:w-72 p-4 rounded-2xl md:rounded-[2rem] shadow-xl 
              bg-white/90 dark:bg-[#15152a]/95 backdrop-blur-xl 
              border border-slate-200/[0.8] dark:border-white/[0.1]
              flex flex-col gap-4 overflow-hidden"
          >
            {/* Header: Logo & Branding */}
            <div className="flex items-center gap-3 px-2 group cursor-pointer mb-2">
              <motion.div
                className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-200 dark:shadow-indigo-900/40 shrink-0"
                whileHover={{ rotate: 180 }}
                transition={{ type: "spring", stiffness: 200, damping: 10 }}
              >
                <Infinity className="w-4 h-4 text-white" />
              </motion.div>
              <div className="flex flex-col">
                <h1 className="text-xl font-black tracking-tighter text-slate-900 group-hover:text-indigo-600 transition-colors dark:text-slate-100 dark:group-hover:text-indigo-400">
                  LOOPS
                </h1>
                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest leading-none dark:text-slate-500">
                  Analytics Hub
                </span>
              </div>
            </div>

            {/* Navigation Options */}
            <nav className="flex flex-col space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => handleTabClick(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative
                      ${isActive
                        ? "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-400"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-slate-200"
                      }
                    `}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="kebabActiveNav"
                        className="absolute inset-0 bg-indigo-50 rounded-xl -z-10 border border-indigo-100/50
                          dark:bg-indigo-500/15 dark:border-indigo-500/20"
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                      />
                    )}
                    <Icon
                      className={`w-4 h-4 transition-transform duration-200 ${
                        isActive ? "scale-110 stroke-[2.5px]" : "group-hover:scale-110"
                      }`}
                    />
                    <span className="font-semibold text-sm tracking-tight">{item.label}</span>
                    {isActive && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="ml-auto w-1 h-1 bg-indigo-600 rounded-full dark:bg-indigo-400"
                      />
                    )}
                  </button>
                );
              })}
            </nav>

            {/* Bottom Actions */}
            <div className="border-t border-slate-100 dark:border-white/[0.07] pt-3 space-y-2">
              {/* Theme Toggle Button */}
              <button
                id="theme-toggle-btn"
                onClick={toggleTheme}
                aria-label="Toggle light/dark theme"
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg
                  text-slate-500 hover:bg-slate-50 hover:text-slate-900
                  dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-slate-200
                  transition-colors group"
              >
                <div className="w-6 h-6 rounded flex items-center justify-center bg-slate-100 dark:bg-white/5 group-hover:bg-white dark:group-hover:bg-white/10 transition-colors">
                  {theme === "light" ? (
                    <Moon className="w-3.5 h-3.5" />
                  ) : (
                    <Sun className="w-3.5 h-3.5" />
                  )}
                </div>
                <span className="text-xs font-semibold uppercase tracking-wider">
                  {theme === "light" ? "Dark Mode" : "Light Mode"}
                </span>
              </button>

              {/* Engine Status */}
              <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50/50 dark:bg-emerald-500/10 rounded-lg">
                <div className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                  Engine Online
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
