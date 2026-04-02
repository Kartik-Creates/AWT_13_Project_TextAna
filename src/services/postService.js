import API from "./api";

/**
 * Post service
 * Endpoints: GET /api/posts/, POST /api/posts/, GET /api/posts/{id}, etc.
 */

export const postService = {
  /**
   * Get paginated feed
   * @param {number} page  — 1-indexed page number
   * @param {number} limit — posts per page
   */
  async getFeed(page = 1, limit = 20) {
    const skip = (page - 1) * limit;
    const { data } = await API.get("/api/posts/", {
      params: { skip, limit },
    });
    return data;
  },

  /**
   * Create a new post (FormData for text + optional image)
   * @param {{ text: string, image?: File }} postData
   */
  async createPost({ text, image }) {
    const formData = new FormData();
    if (text) formData.append("text", text);
    if (image) formData.append("image", image);

    const { data } = await API.post("/api/posts/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  /**
   * Get a single post by id
   * @param {string} postId
   */
  async getPost(postId) {
    const { data } = await API.get(`/api/posts/${postId}`);
    return data;
  },

  /**
   * Delete a post
   * @param {string} postId
   */
  async deletePost(postId) {
    const { data } = await API.delete(`/api/posts/${postId}`);
    return data;
  },

  /**
   * Reprocess a post through moderation
   * @param {string} postId
   */
  async reprocessPost(postId) {
    const { data } = await API.post(`/api/posts/${postId}/reprocess`);
    return data;
  },
};

export default postService;
