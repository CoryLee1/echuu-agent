"""数据模型定义（Pydantic）"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


# ========== 角色相关 ==========

class VoiceConfigCreate(BaseModel):
    """声音配置创建"""
    voice_name: str
    tts_model: str = "qwen3-tts-flash-realtime"
    is_default: bool = False
    priority: int = 0


class VoiceConfigResponse(BaseModel):
    """声音配置响应"""
    id: str
    voice_name: str
    tts_model: str
    is_default: bool
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


class CharacterCreate(BaseModel):
    """角色创建请求"""
    name: str
    persona: str
    background: Optional[str] = None
    avatar_url: Optional[str] = None
    default_llm_model_id: Optional[str] = None
    default_3d_model_id: Optional[str] = None
    voice_configs: List[VoiceConfigCreate] = []


class CharacterUpdate(BaseModel):
    """角色更新请求"""
    name: Optional[str] = None
    persona: Optional[str] = None
    background: Optional[str] = None
    avatar_url: Optional[str] = None
    default_llm_model_id: Optional[str] = None
    default_3d_model_id: Optional[str] = None
    is_active: Optional[bool] = None


class CharacterResponse(BaseModel):
    """角色响应"""
    id: str
    name: str
    persona: str
    background: Optional[str]
    avatar_url: Optional[str]
    default_llm_model_id: Optional[str]
    default_3d_model_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    voice_configs: List[VoiceConfigResponse] = []

    class Config:
        from_attributes = True


class CharacterConfig(BaseModel):
    """角色配置（向后兼容）"""
    name: str = "六螺"
    persona: str = "性格古怪、碎碎念"
    background: str = "直播间"


# ========== 直播相关 ==========

class LiveConfig(BaseModel):
    """直播配置"""
    topic: str = "关于上司的八卦"
    initial_danmaku: Optional[List[str]] = []
    tts_model: Optional[str] = None  # 向后兼容，优先使用 voice_config_id
    tts_voice: Optional[str] = None  # 向后兼容，优先使用 voice_config_id
    max_steps: int = 15
    character_id: Optional[str] = None
    llm_model_id: Optional[str] = None
    voice_config_id: Optional[str] = None
    vtuber_3d_model_id: Optional[str] = None


class SessionInfo(BaseModel):
    """Session 信息"""
    session_id: str
    topic: str
    name: str
    timestamp: str


class StatusResponse(BaseModel):
    """状态响应"""
    is_running: bool
    session_id: str | None


# ========== LLM模型相关 ==========

class LLMModelCreate(BaseModel):
    """LLM模型创建"""
    name: str
    provider: str  # anthropic, openai, custom
    model_id: str
    api_key_env: str
    is_default: bool = False
    config: dict = {}


class LLMModelResponse(BaseModel):
    """LLM模型响应"""
    id: str
    name: str
    provider: str
    model_id: str
    api_key_env: str
    is_default: bool
    config: dict
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 3D模型相关 ==========

class VTuber3DModelCreate(BaseModel):
    """3D模型创建"""
    name: str
    model_path: str
    provider: str  # vrm, glb, custom
    preview_image_url: Optional[str] = None
    config: dict = {}
    is_default: bool = False


class VTuber3DModelResponse(BaseModel):
    """3D模型响应"""
    id: str
    name: str
    model_path: str
    provider: str
    preview_image_url: Optional[str]
    config: dict
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 系统设置相关 ==========

class SystemSettingCreate(BaseModel):
    """系统设置创建"""
    key: str
    value: str
    category: str  # tts, llm, general
    description: Optional[str] = None


class SystemSettingResponse(BaseModel):
    """系统设置响应"""
    id: str
    key: str
    value: str
    category: str
    description: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True
