import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

const TOKEN_KEY = 'skillsetu_auth_token';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.localStorage?.getItem(TOKEN_KEY) || null;
    }
    return null;
  });
  const [loading, setLoading] = useState(true);

  // Restore authenticated session on initial mount
  useEffect(() => {
    let mounted = true;
    async function restoreSession() {
      const storedToken = typeof window !== 'undefined' ? window.localStorage?.getItem(TOKEN_KEY) : null;
      if (!storedToken) {
        if (mounted) {
          setUser(null);
          setLoading(false);
        }
        return;
      }

      try {
        const res = await api.getMe();
        if (mounted && res?.user) {
          setUser(res.user);
          setToken(storedToken);
        } else {
          if (mounted) {
            window.localStorage?.removeItem(TOKEN_KEY);
            setUser(null);
            setToken(null);
          }
        }
      } catch (err) {
        console.warn('[SkillSetu Auth] Session restore failed:', err.message);
        if (mounted) {
          window.localStorage?.removeItem(TOKEN_KEY);
          setUser(null);
          setToken(null);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    restoreSession();
    return () => {
      mounted = false;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await api.login(email, password);
    if (res?.access_token && res?.user) {
      if (typeof window !== 'undefined') {
        window.localStorage?.setItem(TOKEN_KEY, res.access_token);
      }
      setToken(res.access_token);
      setUser(res.user);
      return res.user;
    }
    throw new Error('Authentication failed: missing token or user payload');
  }, []);

  const register = useCallback(async (userData) => {
    const res = await api.register(userData);
    if (res?.access_token && res?.user) {
      if (typeof window !== 'undefined') {
        window.localStorage?.setItem(TOKEN_KEY, res.access_token);
      }
      setToken(res.access_token);
      setUser(res.user);
      return res.user;
    }
    throw new Error('Registration failed: missing token or user payload');
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Ignore network errors on logout
    } finally {
      if (typeof window !== 'undefined') {
        window.localStorage?.removeItem(TOKEN_KEY);
      }
      setToken(null);
      setUser(null);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const res = await api.getMe();
      if (res?.user) {
        setUser(res.user);
        return res.user;
      }
    } catch (err) {
      console.warn('[SkillSetu Auth] Failed refreshing user profile:', err);
    }
    return null;
  }, []);

  const value = {
    user,
    token,
    role: user?.role ? user.role.toUpperCase() : null,
    isAuthenticated: !!user,
    loading,
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
