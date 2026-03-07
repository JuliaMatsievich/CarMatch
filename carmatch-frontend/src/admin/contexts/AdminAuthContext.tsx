import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { setAuthToken } from "../../api/client";
import type { AuthUser } from "../../api/auth";

const ADMIN_TOKEN_KEY = "carmatch_admin_access_token";
const ADMIN_USER_KEY = "carmatch_admin_user";

interface AdminAuthState {
  token: string | null;
  user: AuthUser | null;
  isLoading: boolean;
}

interface AdminAuthContextValue extends AdminAuthState {
  login: (accessToken: string, user: AuthUser) => void;
  logout: () => void;
}

const AdminAuthContext = createContext<AdminAuthContextValue | null>(null);

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AdminAuthState>({
    token: null,
    user: null,
    isLoading: true,
  });

  useEffect(() => {
    const token = localStorage.getItem(ADMIN_TOKEN_KEY);
    const userJson = localStorage.getItem(ADMIN_USER_KEY);
    let user: AuthUser | null = null;
    if (userJson) {
      try {
        user = JSON.parse(userJson) as AuthUser;
      } catch {
        localStorage.removeItem(ADMIN_USER_KEY);
      }
    }
    if (token && user && user.is_admin) {
      setAuthToken(token);
      setState({ token, user, isLoading: false });
    } else {
      setAuthToken(null);
      setState({ token: null, user: null, isLoading: false });
    }
  }, []);

  const login = useCallback((accessToken: string, user: AuthUser) => {
    if (!user.is_admin) {
      throw new Error("Пользователь не является администратором");
    }
    localStorage.setItem(ADMIN_TOKEN_KEY, accessToken);
    localStorage.setItem(ADMIN_USER_KEY, JSON.stringify(user));
    setAuthToken(accessToken);
    setState({ token: accessToken, user, isLoading: false });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(ADMIN_USER_KEY);
    setAuthToken(null);
    setState({ token: null, user: null, isLoading: false });
  }, []);

  const value: AdminAuthContextValue = {
    ...state,
    login,
    logout,
  };

  return (
    <AdminAuthContext.Provider value={value}>
      {children}
    </AdminAuthContext.Provider>
  );
}

// Hook export is intentional; react-refresh expects only components in this file.
// eslint-disable-next-line react-refresh/only-export-components
export function useAdminAuth(): AdminAuthContextValue {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) {
    throw new Error("useAdminAuth must be used within AdminAuthProvider");
  }
  return ctx;
}

