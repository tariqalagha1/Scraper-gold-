/**
 * AuthContext.js
 * 
 * React Context for authentication state management.
 * Provides user authentication state, login/logout functionality,
 * and token management throughout the application.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api, { extractApiErrorMessage } from '../services/api';

/**
 * Auth Context - provides authentication state and methods
 */
const AuthContext = createContext(null);

/**
 * Custom hook to use auth context
 * @returns {Object} Auth context value
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

/**
 * AuthProvider component
 * Wraps the application and provides authentication state
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Check if user is authenticated on mount
   */
  useEffect(() => {
    checkAuth();
  }, []);

  /**
   * Check authentication status
   * Verifies stored token and fetches current user
   */
  const checkAuth = async () => {
    const token = localStorage.getItem('access_token');

    if (!token) {
      setLoading(false);
      return;
    }

    try {
      // Try to get current user from API
      const currentUser = await api.getCurrentUser();
      setUser(currentUser);
      localStorage.setItem('user', JSON.stringify(currentUser));
    } catch (err) {
      // Token is invalid, clear storage
      console.error('Auth check failed:', err);
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Login user with email and password
   * @param {string} email - User email
   * @param {string} password - User password
   * @returns {Promise<Object>} - Login result
   */
  const login = useCallback(async (email, password) => {
    setError(null);
    setLoading(true);

    try {
      const response = await api.login(email, password);
      const { access_token, user: userData } = response;

      // Store token and user data
      localStorage.setItem('access_token', access_token);
      if (userData) {
        localStorage.setItem('user', JSON.stringify(userData));
        setUser(userData);
      }

      // Fetch user data if not returned with token
      if (!userData) {
        const currentUser = await api.getCurrentUser();
        localStorage.setItem('user', JSON.stringify(currentUser));
        setUser(currentUser);
      }

      return { success: true };
    } catch (err) {
      const message = err.response?.data?.detail || 'Login failed. Please try again.';
      setError(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Register a new user
   * @param {Object} userData - User registration data
   * @returns {Promise<Object>} - Registration result
   */
  const register = useCallback(async (userData) => {
    setError(null);
    setLoading(true);

    try {
      await api.register(userData);
      // Auto-login after successful registration
      return await login(userData.email, userData.password);
    } catch (err) {
      const message = extractApiErrorMessage(err, 'Registration failed. Please try again.');
      setError(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  }, [login]);

  /**
   * Logout current user
   * Clears stored tokens and user data
   */
  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
    setError(null);
  }, []);

  /**
   * Clear authentication error
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Check if user is authenticated
   */
  const isAuthenticated = !!user;

  /**
   * Context value
   */
  const value = {
    user,
    loading,
    error,
    isAuthenticated,
    login,
    logout,
    register,
    clearError,
    checkAuth,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
