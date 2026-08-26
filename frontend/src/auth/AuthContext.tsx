import { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';
import type { User, AuthResponse } from '../types';
import { apiClient } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (credentials: { email: string; password: string }) => Promise<void>;
  register: (data: { email: string; password: string; fullName: string }) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('penny_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('penny_token'));

  const setAuthData = (data: AuthResponse) => {
    const userData: User = { email: data.email, fullName: data.fullName };
    setToken(data.accessToken);
    setUser(userData);
    localStorage.setItem('penny_token', data.accessToken);
    localStorage.setItem('penny_user', JSON.stringify(userData));
  };

  const login = async (credentials: { email: string; password: string }) => {
    const data = await apiClient<AuthResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    setAuthData(data);
  };

  const register = async (data: { email: string; password: string; fullName: string }) => {
    const res = await apiClient<AuthResponse>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    setAuthData(res);
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('penny_token');
    localStorage.removeItem('penny_user');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}