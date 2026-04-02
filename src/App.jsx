import { useState } from "react";
import KebabMenu from "./components/KebabMenu";
import AnalyticsPage from "./pages/AnalyticsPage";
import FeedPage from "./pages/FeedPage";
import Loader from "./components/Loader";
import MetricsDashboardPage from "./pages/MetricsDashboardPage";
import usePosts from "./hooks/usePosts";
import { Infinity } from "lucide-react";

import { motion, AnimatePresence } from "framer-motion";

function App() {
  const [activeTab, setActiveTab] = useState("feed");

  // Centralised post state via custom hook
  const {
    posts,
    setPosts,
    loading: isLoading,
    isSubmitting,
    createPost,
    loadMore,
    loadingMore,
    hasMore,
  } = usePosts();

  // Page Transition variants
  const pageVariants = {
    initial: { opacity: 0, y: 10, scale: 0.98 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: -10, scale: 0.98 }
  };

  const pageTransition = {
    type: "spring",
    stiffness: 260,
    damping: 20
  };

  return (
    <div className="flex w-full min-h-screen justify-center">
      {/* Persistent Global Logo */}
      <div className="fixed top-4 left-4 sm:top-5 sm:left-6 z-40 flex items-center gap-3 px-2 group cursor-pointer">
        <motion.div
          className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-200 dark:shadow-indigo-900/40 shrink-0"
          whileHover={{ rotate: 180 }}
          transition={{ type: "spring", stiffness: 200, damping: 10 }}
          onClick={() => setActiveTab("feed")}
        >
          <Infinity className="w-5 h-5 text-white" />
        </motion.div>
        <div className="flex flex-col hidden sm:flex" onClick={() => setActiveTab("feed")}>
          <h1 className="text-2xl font-black tracking-tighter text-slate-900 group-hover:text-indigo-600 transition-colors dark:text-slate-100 dark:group-hover:text-indigo-400">
            LOOPS
          </h1>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none dark:text-slate-500">
            Analytics Hub
          </span>
        </div>
      </div>

      {/* Navigation Kebab Menu */}
      <KebabMenu activeTab={activeTab} setActiveTab={setActiveTab} />
      
      {/* Main Content Area */}
      <main className="w-full max-w-7xl px-4 py-8 pt-20 sm:px-6 lg:px-8 overflow-y-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
            className="w-full h-full"
          >
            {activeTab === "analytics" && <AnalyticsPage />}
            {activeTab === "metrics" && <MetricsDashboardPage />}
            
            {activeTab === "feed" && (
              <FeedPage
                posts={posts}
                setPosts={setPosts}
                isLoading={isLoading}
                loadMore={loadMore}
                loadingMore={loadingMore}
                hasMore={hasMore}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;
