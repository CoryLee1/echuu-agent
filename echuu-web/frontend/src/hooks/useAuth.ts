import { useState, useEffect, useCallback } from "react";
import { login as apiLogin, register as apiRegister, getCurrentUser } from "../api/authApi";
import type { User, LoginRequest, RegisterRequest } from "../types";

const TOKEN_KEY = "echuu.token";
const USER_KEY = "echuu.user";

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // 从 localStorage 恢复用户状态
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    const userStr = localStorage.getItem(USER_KEY);
    
    if (token && userStr) {
      try {
        setUser(JSON.parse(userStr));
      } catch {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      }
    }
    
    // 验证 token 有效性
    if (token) {
      getCurrentUser()
        .then((userData) => {
          setUser(userData);
          localStorage.setItem(USER_KEY, JSON.stringify(userData));
        })
        .catch(() => {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (data: LoginRequest) => {
    const response = await apiLogin(data);
    localStorage.setItem(TOKEN_KEY, response.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(response.user));
    setUser(response.user);
    return response;
  }, []);

  const register = useCallback(async (data: RegisterRequest) => {
    const userData = await apiRegister(data);
    // 注册后自动登录
    await login({ username: data.username, password: data.password });
    return userData;
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  const isAuthenticated = !!user;
  const isAdmin = user?.role === "admin";

  return {
    user,
    loading,
    isAuthenticated,
    isAdmin,
    login,
    register,
    logout,
  };
};

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};
