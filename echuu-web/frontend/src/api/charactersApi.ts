import type { CharacterProfile, CharacterCreate, VoiceConfig, VoiceConfigCreate } from "../types";
import { getToken } from "../hooks/useAuth";

const API_BASE = "http://localhost:8000";

const getHeaders = () => {
  const token = getToken();
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

export const fetchCharacters = async (): Promise<CharacterProfile[]> => {
  const res = await fetch(`${API_BASE}/api/characters`, {
    headers: getHeaders(),
  });

  if (!res.ok) {
    throw new Error("获取角色列表失败");
  }

  return res.json();
};

export const fetchCharacter = async (id: string): Promise<CharacterProfile> => {
  const res = await fetch(`${API_BASE}/api/characters/${id}`, {
    headers: getHeaders(),
  });

  if (!res.ok) {
    throw new Error("获取角色失败");
  }

  return res.json();
};

export const createCharacter = async (data: CharacterCreate): Promise<CharacterProfile> => {
  const res = await fetch(`${API_BASE}/api/characters`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "创建角色失败");
  }

  return res.json();
};

export const updateCharacter = async (
  id: string,
  data: Partial<CharacterCreate>
): Promise<CharacterProfile> => {
  const res = await fetch(`${API_BASE}/api/characters/${id}`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "更新角色失败");
  }

  return res.json();
};

export const deleteCharacter = async (id: string): Promise<void> => {
  const res = await fetch(`${API_BASE}/api/characters/${id}`, {
    method: "DELETE",
    headers: getHeaders(),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "删除角色失败");
  }
};

// ========== 声音配置管理 ==========

export const addVoiceConfig = async (
  characterId: string,
  data: VoiceConfigCreate
): Promise<VoiceConfig> => {
  const res = await fetch(`${API_BASE}/api/characters/${characterId}/voices`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "添加声音配置失败");
  }

  return res.json();
};

export const updateVoiceConfig = async (
  characterId: string,
  voiceId: string,
  data: VoiceConfigCreate
): Promise<VoiceConfig> => {
  const res = await fetch(`${API_BASE}/api/characters/${characterId}/voices/${voiceId}`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "更新声音配置失败");
  }

  return res.json();
};

export const deleteVoiceConfig = async (characterId: string, voiceId: string): Promise<void> => {
  const res = await fetch(`${API_BASE}/api/characters/${characterId}/voices/${voiceId}`, {
    method: "DELETE",
    headers: getHeaders(),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "删除声音配置失败");
  }
};
