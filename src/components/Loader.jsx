import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";

export default function Loader({ message = "Analyzing content..." }) {
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
    >
      <div className="bg-white p-8 rounded-2xl shadow-2xl flex flex-col items-center gap-6 max-w-sm w-full mx-4 glass-panel border border-white/50 relative overflow-hidden">
        {/* Subtle glowing background effect */}
        <div className="absolute inset-0 bg-gradient-to-tr from-indigo-50 to-purple-50 opacity-50" />
        
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
          className="relative z-10"
        >
          <div className="w-16 h-16 rounded-full border-4 border-indigo-100 flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-indigo-600" />
          </div>
          {/* Outer glow ring */}
          <div className="absolute inset-0 rounded-full border-t-4 border-purple-500 blur-[2px]" />
        </motion.div>
        
        <div className="text-center relative z-10 space-y-2">
          <h3 className="text-lg font-semibold text-gray-800 tracking-tight">Processing</h3>
          <p className="text-sm text-gray-500 animate-pulse">{message}</p>
        </div>
      </div>
    </motion.div>
  );
}
