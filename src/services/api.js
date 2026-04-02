import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  headers: { "Content-Type": "application/json" },
});

// ── Request interceptor: attach JWT token ──────────────────────────────
API.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor: 401 → redirect to login ─────────────────────
API.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      // If using a router, redirect to /login
      // window.location.href = "/login";
      console.warn("Unauthorized – token removed");
    }
    return Promise.reject(error);
  }
);

export default API;
