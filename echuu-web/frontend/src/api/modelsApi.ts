import type { LLMModel, VTuber3DModel } from "../types";
import { getToken } from "../hooks/useAuth";

const API_BASE = "http://localhost:8000";

const getHeaders = () => {
  const token = getToken();
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

// ========== LLM模型 ==========

export const fetchLLMModels = async (): Promise<LLMModel[]> => {
  const res = await fetch(`${API_BASE}/api/models/llm`, {
    headers: getHeaders(),
  });

  if (!res.ok) {
    throw new Error("获取LLM模型列表失败");
  }

  return res.json();
};

export const createLLMModel = async (data: Partial<LLMModel>): Promise<LLMModel> => {
  const res = await fetch(`${API_BASE}/api/models/llm`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "创建LLM模型失败");
  }

  return res.json();
};

export const updateLLMModel = async (id: string, data: Partial<LLMModel>): Promise<LLMModel> => {
  const res = await fetch(`${API_BASE}/api/models/llm/${id}`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "更新LLM模型失败");
  }

  return res.json();
};

export const deleteLLMModel = async (id: string): Promise<void> => {
  const res = await fetch(`${API_BASE}/api/models/llm/${id}`, {
    method: "DELETE",
    headers: getHeaders(),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "删除LLM模型失败");
  }
};

// ========== 3D模型 ==========

export const fetch3DModels = async (): Promise<VTuber3DModel[]> => {
  const res = await fetch(`${API_BASE}/api/models/3d`, {
    headers: getHeaders(),
  });

  if (!res.ok) {
    throw new Error("获取3D模型列表失败");
  }

  return res.json();
};

export const upload3DModel = async (
  file: File,
  name?: string,
  provider: string = "vrm"
): Promise<VTuber3DModel> => {
  const formData = new FormData();
  formData.append("file", file);
  if (name) formData.append("name", name);
  formData.append("provider", provider);

  const token = getToken();
  const res = await fetch(`${API_BASE}/api/models/3d/upload`, {
    method: "POST",
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "上传3D模型失败");
  }

  return res.json();
};

export const create3DModel = async (data: Partial<VTuber3DModel>): Promise<VTuber3DModel> => {
  const res = await fetch(`${API_BASE}/api/models/3d`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "创建3D模型失败");
  }

  return res.json();
};

export const update3DModel = async (
  id: string,
  data: Partial<VTuber3DModel>
): Promise<VTuber3DModel> => {
  const res = await fetch(`${API_BASE}/api/models/3d/${id}`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "更新3D模型失败");
  }

  return res.json();
};

export const delete3DModel = async (id: string): Promise<void> => {
  const res = await fetch(`${API_BASE}/api/models/3d/${id}`, {
    method: "DELETE",
    headers: getHeaders(),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "删除3D模型失败");
  }
};
