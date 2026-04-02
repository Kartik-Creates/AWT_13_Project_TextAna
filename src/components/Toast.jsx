import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, Loader2, AlertCircle } from "lucide-react";
import { useEffect } from "react";

export default function Toast({ message, type, onClose }) {
  useEffect(() => {
    if (type !== "loading") {
      const timer = setTimeout(() => {
        onClose();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [type, onClose]);

  if (!message) return null;

  const styles = {
    loading: "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800",
    success: "bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800",
    error: "bg-rose-50 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800",
  };

  const icons = {
    loading: <Loader2 className="w-5 h-5 animate-spin text-blue-600" />,
    success: <CheckCircle2 className="w-5 h-5 text-green-600" />,
    error: <AlertCircle className="w-5 h-5 text-rose-600" />,
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 50, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center justify-center pointer-events-none px-4 w-full max-w-lg"
      >
        <div 
          className={`flex items-start gap-3 px-4 py-3 rounded-2xl border shadow-lg backdrop-blur-md pointer-events-auto transition-colors w-full ${styles[type] || styles.loading}`}
        >
          <div className="shrink-0 mt-0.5">
            {icons[type]}
          </div>
          <div className="flex-1 text-sm font-medium pr-2 break-words">
            {message}
          </div>
          {type !== "loading" && (
            <button 
              onClick={onClose}
              className="shrink-0 rounded-full p-1 opacity-60 hover:opacity-100 transition-opacity focus:outline-none"
            >
              <XCircle className="w-4 h-4" />
            </button>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
