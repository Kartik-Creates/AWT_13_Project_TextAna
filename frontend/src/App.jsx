import { useState } from "react";
import Sidebar from "./components/Sidebar";
import AnalyticsPage from "./pages/AnalyticsPage";
import FeedPage from "./pages/FeedPage";
import CreatePost from "./components/CreatePost";
import Loader from "./components/Loader";
import MetricsDashboardPage from "./pages/MetricsDashboardPage";
import usePosts from "./hooks/usePosts";

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

  const handleCreatePost = async ({ text, image }) => {
    try {
      await createPost({ text, image });
      // Switch to feed after successful creation
      setActiveTab("feed");
    } catch (error) {
      alert("Failed to process content. Make sure backend is running.");
    }
  };

  return (
    <div className="flex w-full min-h-screen">
      {/* Sidebar Navigation */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      {/* Main Content Area */}
      <main className="flex-1 ml-64 p-4 sm:p-8 overflow-y-auto">
        {activeTab === "analytics" && <AnalyticsPage />}
        {activeTab === "metrics" && <MetricsDashboardPage />}
        
        {activeTab === "create" && (
          <div className="max-w-3xl mx-auto mt-10">
            <div className="mb-8 text-center">
              <h2 className="text-3xl font-bold text-gray-900 tracking-tight">Create Post</h2>
              <p className="text-gray-500 mt-2">Content is instantly analyzed by the verification engine before publishing.</p>
            </div>
            <CreatePost onSubmit={handleCreatePost} isSubmitting={isSubmitting} />
          </div>
        )}

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
        
        {/* Global Loading Overlay triggered from Create Tab */}
        {isSubmitting && activeTab === 'create' && <Loader />}
      </main>
    </div>
  );
}

export default App;
