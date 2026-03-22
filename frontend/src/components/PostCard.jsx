import { motion } from "framer-motion";
import { ShieldCheck, ShieldAlert, ShieldQuestion, MoreHorizontal, MessageCircle, Repeat2, Heart, Share } from "lucide-react";

export default function PostCard({ post }) {
  // Backend returns flat: { allowed: true/false/null, reasons: [...], flagged_phrases: [...] }
  const isAllowed = post.allowed;
  const isPending = post.allowed === null || post.allowed === undefined;
  
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ y: -4, scale: 1.01 }}
      transition={{ type: "spring", stiffness: 400, damping: 17 }}
      className={`rounded-2xl p-4 sm:p-5 mb-4 transition-all cursor-pointer group shadow-sm hover:shadow-md ${
        isPending
          ? "glass-panel border border-amber-200 hover:bg-amber-50/60"
          : isAllowed 
            ? "glass-panel border border-gray-100 hover:bg-white/60" 
            : "bg-rose-50/70 border border-rose-200 hover:bg-rose-100/60"
      }`}
    >
      <div className="flex gap-4 relative">
        {/* Avatar */}
        <div className="shrink-0">
          <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-indigo-100 to-purple-100 border-2 border-white shadow-sm flex items-center justify-center font-bold text-indigo-700">
            U
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5 truncate">
              <span className="font-bold text-gray-900 truncate hover:underline">User Name</span>
              <span className="text-gray-500 text-sm truncate">@username · 2h</span>
            </div>
            <button className="text-gray-400 hover:text-indigo-600 p-1.5 rounded-full hover:bg-indigo-50 transition-colors">
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>

          {/* Text Content */}
          <p className="text-gray-800 text-[15px] leading-relaxed mb-3 whitespace-pre-wrap word-break">
            {post.text}
          </p>

          {/* Image — backend sends image_path */}
          {post.image_path && (
            <div className="mt-3 rounded-2xl overflow-hidden border border-gray-100 mb-3 bg-gray-50 max-h-[400px]">
              <img 
                src={`http://localhost:8000${post.image_path.startsWith('/uploads') ? post.image_path : '/uploads' + (post.image_path.startsWith('/') ? '' : '/') + post.image_path}`}
                alt="Post content" 
                className="w-full h-full object-cover"
              />
            </div>
          )}

          {/* Moderation Badge */}
          <div className="mt-4 mb-2">
            {isPending ? (
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-100 text-amber-700 text-sm font-medium shadow-[0_0_15px_rgba(245,158,11,0.15)]">
                <ShieldQuestion className="w-4 h-4" />
                <span>Pending: Awaiting moderation</span>
              </div>
            ) : isAllowed ? (
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-sm font-medium shadow-[0_0_15px_rgba(16,185,129,0.15)]">
                <ShieldCheck className="w-4 h-4" />
                <span>Allowed: Content approved</span>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-50 border border-rose-100 text-rose-700 text-sm font-medium shadow-[0_0_15px_rgba(244,63,63,0.15)]">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Blocked</span>
                </div>
                
                {post.reasons && post.reasons.length > 0 && (
                  <div className="text-sm text-rose-600 bg-rose-50/50 p-2.5 rounded-lg border border-rose-100 inline-block max-w-full truncate">
                    Reason: {post.reasons[0]}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Social Actions */}
          <div className="flex items-center justify-between text-gray-400 mt-4 max-w-sm">
            <button className="flex items-center gap-2 hover:text-indigo-600 group/btn transition-colors">
              <div className="p-2 rounded-full group-hover/btn:bg-indigo-50 transition-colors">
                <MessageCircle className="w-4 h-4" />
              </div>
              <span className="text-xs">24</span>
            </button>
            <button className="flex items-center gap-2 hover:text-emerald-600 group/btn transition-colors">
              <div className="p-2 rounded-full group-hover/btn:bg-emerald-50 transition-colors">
                <Repeat2 className="w-4 h-4" />
              </div>
              <span className="text-xs">12</span>
            </button>
            <button className="flex items-center gap-2 hover:text-pink-600 group/btn transition-colors">
              <div className="p-2 rounded-full group-hover/btn:bg-pink-50 transition-colors">
                <Heart className="w-4 h-4" />
              </div>
              <span className="text-xs">148</span>
            </button>
            <button className="flex items-center gap-2 hover:text-indigo-600 group/btn transition-colors">
              <div className="p-2 rounded-full group-hover/btn:bg-indigo-50 transition-colors">
                <Share className="w-4 h-4" />
              </div>
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
