// ========== 用户相关 ==========
export type User = {
  id: string;
  username: string;
  email: string;
  role: "admin" | "user";
  is_active: boolean;
};

export type LoginRequest = {
  username: string;
  password: string;
};

export type RegisterRequest = {
  username: string;
  email: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

// ========== 角色相关 ==========
export type VoiceConfig = {
  id: string;
  voice_name: string;
  tts_model: string;
  is_default: boolean;
  priority: number;
  created_at: string;
};

export type CharacterProfile = {
  id: string;
  name: string;
  persona: string;
  background?: string;
  avatar_url?: string;
  default_llm_model_id?: string;
  default_3d_model_id?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  voice_configs?: VoiceConfig[];
};

export type CharacterCreate = {
  name: string;
  persona: string;
  background?: string;
  avatar_url?: string;
  default_llm_model_id?: string;
  default_3d_model_id?: string;
  voice_configs?: VoiceConfigCreate[];
};

export type VoiceConfigCreate = {
  voice_name: string;
  tts_model?: string;
  is_default?: boolean;
  priority?: number;
};

// ========== 模型相关 ==========
export type LLMModel = {
  id: string;
  name: string;
  provider: "anthropic" | "openai" | "custom";
  model_id: string;
  api_key_env: string;
  is_default: boolean;
  config: Record<string, any>;
  created_at: string;
};

export type VTuber3DModel = {
  id: string;
  name: string;
  model_path: string;
  provider: string;
  preview_image_url?: string;
  config: Record<string, any>;
  is_default: boolean;
  created_at: string;
};

// ========== 直播相关 ==========
export type LiveSession = {
  session_id: string;
  topic: string;
  name: string;
  timestamp: string;
  status?: string;
  started_at?: string;
  ended_at?: string;
};

export type LiveStatus = {
  is_running: boolean;
  session_id: string | null;
};

export type MemorySnapshot = {
  story_points: string[];
  promises: { content: string }[];
  emotion_trend: number[];
};

export type LiveConfig = {
  topic: string;
  initial_danmaku?: string[];
  tts_model?: string;
  tts_voice?: string;
  max_steps?: number;
  character_id?: string;
  llm_model_id?: string;
  voice_config_id?: string;
  vtuber_3d_model_id?: string;
};

// ========== 系统设置相关 ==========
export type SystemSetting = {
  id: string;
  key: string;
  value: string;
  category: string;
  description?: string;
  updated_at: string;
};

// ========== PerformerCue 表演标注 ==========
export type EmotionCue = {
  key: "neutral" | "happy" | "angry" | "sad" | "relaxed" | "surprised" | "fun" | "sorrow";
  intensity: number;
  attack: number;
  release: number;
};

export type GestureCue = {
  clip: string;
  weight: number;
  duration: number;
  loop: boolean;
};

export type LookCue = {
  target: "camera" | "chat" | "offscreen" | "down" | "up" | "left" | "right" | [number, number];
  strength: number;
};

export type BlinkCue = {
  mode: "auto" | "hold" | "none" | "wink_left" | "wink_right";
  extra: number;
};

export type LipsyncCue = {
  enabled: boolean;
  aa: number;
  ih: number;
  ou: number;
  ee: number;
  oh: number;
};

export type CameraCue = {
  preset?: string;
  zoom?: number;
};

export type PerformerCue = {
  emotion?: EmotionCue;
  gesture?: GestureCue;
  look?: LookCue;
  blink?: BlinkCue;
  lipsync?: LipsyncCue;
  camera?: CameraCue;
  beat?: number;
  pause?: number;
};

// ========== VRM 控制指令 ==========
export type VRMCommand = {
  type: "expression" | "gesture" | "lookat";
  blendShape?: string;
  weight?: number;
  fadeIn?: number;
  fadeOut?: number;
  clip?: string;
  duration?: number;
  target?: string | [number, number];
  version?: "vrm0" | "vrm1";
};
