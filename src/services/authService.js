import API from "./api";

/**
 * Authentication service
 * Endpoints: POST /auth/signup, POST /auth/login, GET /auth/me
 */

export const authService = {
  /**
   * Register a new user
   * @param {{ username: string, email: string, password: string }} userData
   */
  async signup(userData) {
    const { data } = await API.post("/auth/signup", userData);
    return data;
  },

  /**
   * Login and store JWT token
   * @param {{ email: string, password: string }} credentials
   * @returns {{ access_token: string, token_type: string }}
   */
  async login(credentials) {
    const { data } = await API.post("/auth/login", credentials);
    if (data.access_token) {
      localStorage.setItem("token", data.access_token);
    }
    return data;
  },

  /**
   * Logout — remove token and redirect
   */
  logout() {
    localStorage.removeItem("token");
    window.location.href = "/";
  },

  /**
   * Get current authenticated user
   */
  async getCurrentUser() {
    const { data } = await API.get("/auth/me");
    return data;
  },

  /**
   * Check if user is logged in (token exists)
   */
  isAuthenticated() {
    return !!localStorage.getItem("token");
  },
};

export default authService;
