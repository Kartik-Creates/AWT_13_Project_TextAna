import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import AnalyticsPage from "./pages/AnalyticsPage";
import FeedPage from "./pages/FeedPage";
import CreatePost from "./components/CreatePost";
import Loader from "./components/Loader";

function App() {
  const [activeTab, setActiveTab] = useState("feed");
  const [posts, setPosts] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        const response = await fetch("/api/posts");
        if (response.ok) {
          const data = await response.json();
          // Assuming the backend returns an array of objects
          if (Array.isArray(data)) {
            // Reverse to show newest at top assuming Mongo returns chronological
            setPosts(data.reverse());
          }
        }
      } catch (error) {
        console.error("Error fetching initial posts:", error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchPosts();
  }, []);

  const handleCreatePost = async ({ text, image }) => {
    setIsSubmitting(true);
    
    try {
      const formData = new FormData();
      if (text) formData.append("text", text);
      if (image) formData.append("image", image);

      const response = await fetch("/api/posts", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to moderate post");
      }

      const result = await response.json();
      
      // Update dummy ID for UI key
      result.id = Date.now().toString();
      
      // Switch to feed and prepend newly analyzed post
      setActiveTab("feed");
      setPosts(prev => [result, ...prev]);

    } catch (error) {
      console.error("Error submitting post:", error);
      alert("Failed to process content. Make sure backend is running.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex w-full min-h-screen">
      {/* Sidebar Navigation */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      {/* Main Content Area */}
      <main className="flex-1 ml-64 p-4 sm:p-8 overflow-y-auto">
        {activeTab === "analytics" && <AnalyticsPage />}
        
        {activeTab === "create" && (
          <div className="max-w-3xl mx-auto mt-10">
            <div className="mb-8 text-center">
              <h2 className="text-3xl font-bold text-gray-900 tracking-tight">Create Post</h2>
              <p className="text-gray-500 mt-2">Content is instantly analyzed by the verification engine before publishing.</p>
            </div>
            <CreatePost onSubmit={handleCreatePost} isSubmitting={isSubmitting} />
          </div>
        )}

        {activeTab === "feed" && <FeedPage posts={posts} setPosts={setPosts} isLoading={isLoading} />}
        
        {/* Global Loading Overlay triggered from Create Tab */}
        {isSubmitting && activeTab === 'create' && <Loader />}
      </main>
    </div>
  );
}

export default App;
