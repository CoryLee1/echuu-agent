import type { LoginRequest, RegisterRequest, TokenResponse, User } from "../types";

const API_BASE = "http://localhost:8000";

export const login = async (data: LoginRequest): Promise<TokenResponse> => {
  const formData = new FormData();
  formData.append("username", data.username);
  formData.append("password", data.password);

  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "登录失败");
  }

  return res.json();
};

export const register = async (data: RegisterRequest): Promise<User> => {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "注册失败");
  }

  return res.json();
};

export const getCurrentUser = async (): Promise<User> => {
  const token = localStorage.getItem("echuu.token");
  if (!token) {
    throw new Error("未登录");
  }

  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem("echuu.token");
      localStorage.removeItem("echuu.user");
      throw new Error("登录已过期");
    }
    throw new Error("获取用户信息失败");
  }

  return res.json();
};
