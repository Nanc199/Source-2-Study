'use client';
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import Cookies from 'js-cookie';
import { auth } from '@/lib/api';

interface User {
  id: number;
  email: string;
  full_name: string;
  is_verified?: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<{ message: string; email?: string }>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => ({ message: '' }),
  logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = Cookies.get('token');
    if (token) {
      auth.getProfile()
        .then((u: User) => setUser(u))
        .catch(() => { Cookies.remove('token'); })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const data = await auth.login({ email, password });
    Cookies.set('token', data.access_token, { expires: 7 });
    if (data.user) {
      setUser(data.user);
    } else {
      const profile = await auth.getProfile();
      setUser(profile);
    }
  };

  const register = async (fullName: string, email: string, password: string) => {
    const data = await auth.register({ full_name: fullName, email, password });
    return data;
  };

  const logout = () => {
    Cookies.remove('token');
    setUser(null);
    if (typeof window !== 'undefined') window.location.href = '/login';
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
