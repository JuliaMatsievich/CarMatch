import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { setAuthToken } from '../api/client';
import type { AuthUser } from '../api/auth';

const TOKEN_KEY = 'carmatch_access_token';
const USER_KEY = 'carmatch_user';

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (accessToken: string, user: AuthUser) => void;
  register: (accessToken: string, user: AuthUser) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: null,
    user: null,
    isLoading: true,
  });

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    const userJson = localStorage.getItem(USER_KEY);
    let user: AuthUser | null = null;
    if (userJson) {
      try {
        user = JSON.parse(userJson) as AuthUser;
      } catch {
        localStorage.removeItem(USER_KEY);
      }
    }
    if (token) {
      setAuthToken(token);
      setState({ token, user, isLoading: false });
    } else {
      setAuthToken(null);
      setState({ token: null, user: null, isLoading: false });
    }
  }, []);

  const login = useCallback((accessToken: string, user: AuthUser) => {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    setAuthToken(accessToken);
    setState({ token: accessToken, user, isLoading: false });
  }, []);

  const register = useCallback((accessToken: string, user: AuthUser) => {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    setAuthToken(accessToken);
    setState({ token: accessToken, user, isLoading: false });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setAuthToken(null);
    setState({ token: null, user: null, isLoading: false });
  }, []);

  const value: AuthContextValue = {
    ...state,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
