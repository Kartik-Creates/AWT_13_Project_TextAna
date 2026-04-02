import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ImagePlus, X, Send } from "lucide-react";

export default function CreatePost({ onSubmit, isSubmitting }) {
  const [text, setText] = useState("");
  const [image, setImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef(null);

  const handleImageChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setImage(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    }
  };

  const removeImage = () => {
    setImage(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = () => {
    if (!text && !image) return;
    onSubmit({ text, image });
    setText("");
    removeImage();
  };

  return (
    <div className="max-w-2xl mx-auto w-full px-2 sm:px-4 pb-8">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-5 sm:p-6 rounded-3xl border border-white/80 dark:border-white/[0.07] shadow-lg shadow-indigo-500/5 dark:shadow-indigo-500/10 group"
      >
        <div className="flex gap-4">
          <div className="shrink-0 pt-1">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold shadow-md shadow-indigo-500/30">
              U
            </div>
          </div>

          <div className="flex-1 space-y-4">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="What's happening?"
              className="w-full bg-transparent text-sm text-gray-800 dark:text-slate-200 placeholder:text-gray-400 dark:placeholder:text-slate-500 resize-none outline-none min-h-[80px]"
              maxLength={280}
            />

            <AnimatePresence>
              {previewUrl && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="relative rounded-2xl overflow-hidden border border-gray-100 dark:border-white/[0.07] group"
                >
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="w-full max-h-[300px] object-cover"
                  />
                  <button
                    onClick={removeImage}
                    className="absolute top-2 right-2 p-1.5 bg-black/50 text-white rounded-full backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="pt-3 flex items-center justify-between border-t border-gray-100 dark:border-white/[0.07]">
              <div className="flex gap-2">
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  ref={fileInputRef}
                  onChange={handleImageChange}
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-2 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/15 rounded-full transition-colors"
                  title="Add Image"
                >
                  <ImagePlus className="w-5 h-5" />
                </button>
              </div>

              <div className="flex items-center gap-4">
                <span className={`text-xs ${text.length > 250 ? 'text-rose-500' : 'text-gray-400 dark:text-slate-500'}`}>
                  {text.length}/280
                </span>

                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting || (!text && !image)}
                  className={`
                    flex items-center gap-2 px-6 py-2 rounded-full font-semibold text-white transition-all duration-300
                    ${isSubmitting || (!text && !image)
                      ? "bg-indigo-300 dark:bg-indigo-800 cursor-not-allowed opacity-70"
                      : "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 shadow-md shadow-indigo-600/30 hover:shadow-lg hover:shadow-indigo-600/40 hover:-translate-y-0.5"
                    }
                  `}
                >
                  <span>Post</span>
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
