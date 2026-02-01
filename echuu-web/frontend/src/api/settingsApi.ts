import type { SystemSetting } from "../types";
import { getToken } from "../hooks/useAuth";

const API_BASE = "http://localhost:8000";

const getHeaders = () => {
  const token = getToken();
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

export const fetchSettings = async (category?: string): Promise<SystemSetting[]> => {
  const url = category
    ? `${API_BASE}/api/settings?category=${category}`
    : `${API_BASE}/api/settings`;
  
  const res = await fetch(url, {
    headers: getHeaders(),
  });

  if (!res.ok) {
    throw new Error("获取系统设置失败");
  }

  return res.json();
};

export const getSetting = async (key: string): Promise<SystemSetting> => {
  const res = await fetch(`${API_BASE}/api/settings/${key}`, {
    headers: getHeaders(),
  });

  if (!res.ok) {
    throw new Error("获取设置项失败");
  }

  return res.json();
};

export const createSetting = async (data: Partial<SystemSetting>): Promise<SystemSetting> => {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "创建设置项失败");
  }

  return res.json();
};

export const updateSetting = async (
  key: string,
  value: string,
  description?: string
): Promise<SystemSetting> => {
  const url = new URL(`${API_BASE}/api/settings/${key}`);
  url.searchParams.append("value", value);
  if (description) url.searchParams.append("description", description);

  const res = await fetch(url.toString(), {
    method: "PUT",
    headers: getHeaders(),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "更新设置项失败");
  }

  return res.json();
};

export const deleteSetting = async (key: string): Promise<void> => {
  const res = await fetch(`${API_BASE}/api/settings/${key}`, {
    method: "DELETE",
    headers: getHeaders(),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "删除设置项失败");
  }
};
