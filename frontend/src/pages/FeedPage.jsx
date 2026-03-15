import { useState } from "react";
import CreatePost from "../components/CreatePost";
import PostCard from "../components/PostCard";
import Loader from "../components/Loader";

export default function Feed({ posts, setPosts, isLoading }) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async ({ text, image }) => {
    setIsSubmitting(true);
    
    try {
      const formData = new FormData();
      if (text) formData.append("text", text);
      if (image) formData.append("image", image);

      const response = await fetch("/api/posts/", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to moderate post");
      }

      const result = await response.json();
      
      // Add the new post to the top of the feed
      setPosts(prev => [result, ...prev]);

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
      </div>

      {isSubmitting && <Loader />}
    </div>
  );
}
