/**
 * Authentication Context for managing user state
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi, setAuthToken } from '../services/auth';

interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login: string | null;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load token from localStorage on mount
  useEffect(() => {
    const loadAuth = async () => {
      const storedToken = localStorage.getItem('auth_token');

      if (storedToken) {
        setToken(storedToken);
        setAuthToken(storedToken);

        try {
          // Verify token and get user data. If the backend is unreachable
          // (e.g. the user clicked an email link but their local FastAPI
          // isn't running) we race against a hard timeout so the UI falls
          // back to the login screen instead of an infinite spinner.
          const userData = await Promise.race([
            authApi.getCurrentUser(),
            new Promise<never>((_, reject) =>
              setTimeout(
                () => reject(new Error('auth_bootstrap_timeout')),
                8000,
              ),
            ),
          ]);
          setUser(userData);
        } catch (error) {
          console.error('Failed to load user data:', error);
          // Clear the stale token so /login renders cleanly. We don't
          // nuke it on genuine network blips alone — but since we can
          // retry by refreshing, this is the safe default.
          localStorage.removeItem('auth_token');
          setToken(null);
          setAuthToken(null);
        }
      }

      setIsLoading(false);
    };

    loadAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await authApi.login(email, password);
    const newToken = response.access_token;

    setToken(newToken);
    localStorage.setItem('auth_token', newToken);
    setAuthToken(newToken);

    // Fetch user data
    const userData = await authApi.getCurrentUser();
    setUser(userData);
  };

  const signup = async (email: string, password: string, fullName?: string) => {
    await authApi.signup(email, password, fullName);
    // Don't auto-login after signup - user needs to verify email first
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('auth_token');
    setAuthToken(null);
  };

  const refreshUser = async () => {
    if (token) {
      try {
        const userData = await authApi.getCurrentUser();
        setUser(userData);
      } catch (error) {
        console.error('Failed to refresh user data:', error);
        logout();
      }
    }
  };

  const value: AuthContextType = {
    user,
    token,
    isLoading,
    isAuthenticated: !!user && !!token,
    login,
    signup,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
