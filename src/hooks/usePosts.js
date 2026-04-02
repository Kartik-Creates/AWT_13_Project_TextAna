import { useState, useEffect, useCallback, useRef } from "react";
import postService from "../services/postService";

const PAGE_SIZE = 20;

/**
 * Custom hook for feed management with infinite scroll support
 */
export function usePosts() {
  const [posts, setPosts] = useState([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const initialLoad = useRef(true);

  // Initial fetch
  useEffect(() => {
    const fetchInitial = async () => {
      try {
        setLoading(true);
        const data = await postService.getFeed(1, PAGE_SIZE);
        setPosts(Array.isArray(data) ? data : []);
        setHasMore(Array.isArray(data) && data.length >= PAGE_SIZE);
        setPage(1);
      } catch (err) {
        console.error("Error fetching posts:", err);
        setError(err.response?.data?.detail || "Failed to load posts");
      } finally {
        setLoading(false);
        initialLoad.current = false;
      }
    };
    fetchInitial();
  }, []);

  // Load more for infinite scroll
  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    try {
      setLoadingMore(true);
      const nextPage = page + 1;
      const data = await postService.getFeed(nextPage, PAGE_SIZE);
      const newPosts = Array.isArray(data) ? data : [];
      setPosts((prev) => [...prev, ...newPosts]);
      setPage(nextPage);
      setHasMore(newPosts.length >= PAGE_SIZE);
    } catch (err) {
      console.error("Error loading more posts:", err);
    } finally {
      setLoadingMore(false);
    }
  }, [page, loadingMore, hasMore]);

  // Create a new post
  const createPost = useCallback(async ({ text, image }) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await postService.createPost({ text, image });
      // Ensure the result has an id
      if (!result.id) {
        result.id = Date.now().toString();
      }
      // Prepend new post to feed
      setPosts((prev) => [result, ...prev]);
      return result;
    } catch (err) {
      console.error("Error creating post:", err);
      const message =
        err.response?.data?.detail || "Failed to process content. Make sure backend is running.";
      setError(message);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  // Refresh the feed
  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await postService.getFeed(1, PAGE_SIZE);
      setPosts(Array.isArray(data) ? data : []);
      setHasMore(Array.isArray(data) && data.length >= PAGE_SIZE);
      setPage(1);
    } catch (err) {
      console.error("Error refreshing posts:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    posts,
    setPosts,
    loading,
    loadingMore,
    hasMore,
    error,
    isSubmitting,
    loadMore,
    createPost,
    refresh,
  };
}

export default usePosts;
