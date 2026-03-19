import { useState, useRef, useEffect, useCallback } from "react";
import CreatePost from "../components/CreatePost";
import PostCard from "../components/PostCard";
import Loader from "../components/Loader";
import postService from "../services/postService";

export default function Feed({ posts, setPosts, isLoading, loadMore, loadingMore, hasMore }) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const sentinelRef = useRef(null);

  // ── Infinite scroll with IntersectionObserver ────────────────────────
  useEffect(() => {
    if (!sentinelRef.current || !loadMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore) {
          loadMore();
        }
      },
      { rootMargin: "200px" }
    );

    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [loadMore, hasMore, loadingMore]);

  // ── Inline post creation (feed page also has a CreatePost) ──────────
  const handleSubmit = async ({ text, image }) => {
    setIsSubmitting(true);
    try {
      const result = await postService.createPost({ text, image });
      if (!result.id) result.id = Date.now().toString();
      setPosts((prev) => [result, ...prev]);
    } catch (error) {
      console.error("Error submitting post:", error);
      alert("Failed to process content. Make sure backend is running.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto w-full pb-20">
      {/* Sticky Header */}
      <div className="sticky top-0 z-10 glass-panel border-b border-gray-200/50 px-4 py-3 pb-4 rounded-b-2xl mb-4">
        <h2 className="text-xl font-bold text-gray-900 tracking-tight">Home</h2>
      </div>

      <CreatePost onSubmit={handleSubmit} isSubmitting={isSubmitting} />

      <div className="h-px bg-gray-200 my-4 w-full" />

      <div className="space-y-1">
        {isLoading ? (
          <div className="flex justify-center p-8">
            <div className="w-8 h-8 rounded-full border-4 border-indigo-200 border-t-indigo-600 animate-spin" />
          </div>
        ) : posts.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-lg font-medium">No posts yet</p>
            <p className="text-sm">Be the first to create a post!</p>
          </div>
        ) : (
          posts.map((post, idx) => (
            <PostCard key={post.id || post._id || idx} post={post} />
          ))
        )}

        {/* Infinite scroll sentinel */}
        {!isLoading && hasMore && (
          <div ref={sentinelRef} className="flex justify-center p-4">
            {loadingMore && (
              <div className="w-6 h-6 rounded-full border-3 border-indigo-200 border-t-indigo-600 animate-spin" />
            )}
          </div>
        )}

        {/* End of feed */}
        {!isLoading && !hasMore && posts.length > 0 && (
          <div className="text-center py-6 text-gray-400 text-sm">
            You've reached the end of the feed
          </div>
        )}
      </div>

      {isSubmitting && <Loader />}
    </div>
  );
}
