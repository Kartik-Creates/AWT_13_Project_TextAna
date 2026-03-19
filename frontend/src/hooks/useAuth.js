import { useState, useEffect, useCallback } from "react";
import authService from "../services/authService";

/**
 * Custom hook for authentication state management
 */
export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check token validity on mount
  useEffect(() => {
    const validateSession = async () => {
      if (!authService.isAuthenticated()) {
        setLoading(false);
        return;
      }
      try {
        const userData = await authService.getCurrentUser();
        setUser(userData);
      } catch (err) {
        console.warn("Session validation failed:", err);
        localStorage.removeItem("token");
      } finally {
        setLoading(false);
      }
    };
    validateSession();
  }, []);

  const login = useCallback(async (credentials) => {
    setError(null);
    setLoading(true);
    try {
      await authService.login(credentials);
      const userData = await authService.getCurrentUser();
      setUser(userData);
      return userData;
    } catch (err) {
      const message = err.response?.data?.detail || "Login failed";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const signup = useCallback(async (userData) => {
    setError(null);
    setLoading(true);
    try {
      const result = await authService.signup(userData);
      return result;
    } catch (err) {
      const message = err.response?.data?.detail || "Signup failed";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  return {
    user,
    loading,
    error,
    login,
    signup,
    logout,
    isAuthenticated: !!user,
  };
}

export default useAuth;
