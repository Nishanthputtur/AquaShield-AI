import React, { createContext, useContext, useEffect, useState } from 'react';
import api from '../services/api';
import {
  clearToken,
  clearUser,
  getToken,
  getUser,
  saveToken,
  saveUser,
} from '../services/auth';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getUser());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    let isMounted = true;
    api
      .getMe(token)
      .then((userData) => {
        if (isMounted) {
          saveUser(userData);
          setUser(userData);
        }
      })
      .catch(() => {
        if (isMounted) {
          clearToken();
          clearUser();
          setUser(null);
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (email, password) => {
    const res = await api.login(email, password);
    const token = res.access_token;
    saveToken(token);
    const userData = await api.getMe(token);
    saveUser(userData);
    setUser(userData);
    return userData;
  };

  const logout = () => {
    clearToken();
    clearUser();
    setUser(null);
  };

  const value = {
    user,
    token: getToken(),
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
