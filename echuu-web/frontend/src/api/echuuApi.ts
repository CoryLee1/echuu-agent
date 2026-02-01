import type { LiveSession, LiveStatus, LiveConfig } from "../types";
import { getToken } from "../hooks/useAuth";

const API_BASE = "http://localhost:8000";

const getHeaders = () => {
  const token = getToken();
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

export const fetchStatus = async (): Promise<LiveStatus> => {
  const res = await fetch(`${API_BASE}/api/status`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error("无法获取直播状态");
  }
  return res.json();
};

export const fetchHistory = async (): Promise<LiveSession[]> => {
  const res = await fetch(`${API_BASE}/api/history`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error("无法获取历史记录");
  }
  return res.json();
};

export const startLive = async (config: LiveConfig) => {
  const res = await fetch(`${API_BASE}/api/start`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || "启动直播失败");
  }
  return res.json();
};

export const sendDanmaku = async (text: string, user = "观众") => {
  const url = `${API_BASE}/api/danmaku?text=${encodeURIComponent(text)}&user=${encodeURIComponent(user)}`;
  const res = await fetch(url, {
    method: "POST",
    headers: getHeaders(),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || "发送弹幕失败");
  }
  return res.json();
};

export const downloadSessionUrl = (sessionId: string) => `${API_BASE}/api/download/${sessionId}`;

export const audioUrl = (path: string) => `${API_BASE}${path}`;
