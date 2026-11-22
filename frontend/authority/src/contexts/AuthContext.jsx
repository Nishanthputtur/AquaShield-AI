import React, { useEffect, useState } from 'react';
import api from '../services/api';
import { AuthContext } from './AuthContextStore';
import {
  clearToken,
  clearUser,
  getToken,
  getUser,
  saveToken,
  saveUser,
} from '../services/auth';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() =>
    getToken() ? getUser() : null);
  const [loading, setLoading] = useState(() => Boolean(getToken()));

  useEffect(() => {
    const token = getToken();
    if (!token) {
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