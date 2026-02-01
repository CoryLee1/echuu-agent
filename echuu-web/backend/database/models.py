"""SQLAlchemy 数据库模型定义"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

try:
    from .database import Base
except ImportError:
    from database import Base


# 使用 SQLite 兼容的 UUID
def generate_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class LLMProvider(str, enum.Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    CUSTOM = "custom"


class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # 关系
    characters = relationship("Character", back_populates="user", cascade="all, delete-orphan")
    live_sessions = relationship("LiveSession", back_populates="user", cascade="all, delete-orphan")


class LLMModel(Base):
    """LLM模型表"""
    __tablename__ = "llm_models"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    provider = Column(Enum(LLMProvider), nullable=False)
    model_id = Column(String(100), nullable=False)
    api_key_env = Column(String(50), nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    characters = relationship("Character", back_populates="default_llm_model", foreign_keys="Character.default_llm_model_id")
    live_sessions = relationship("LiveSession", back_populates="llm_model")


class VTuber3DModel(Base):
    """VTuber 3D模型表"""
    __tablename__ = "vtuber_3d_models"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    model_path = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)  # vrm, glb, custom
    preview_image_url = Column(String(255))
    config = Column(JSON, default=dict)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    characters = relationship("Character", back_populates="default_3d_model", foreign_keys="Character.default_3d_model_id")
    live_sessions = relationship("LiveSession", back_populates="vtuber_3d_model")


class Character(Base):
    """角色表"""
    __tablename__ = "characters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    persona = Column(Text, nullable=False)
    background = Column(Text)
    avatar_url = Column(String(255))
    default_llm_model_id = Column(String(36), ForeignKey("llm_models.id"))
    default_3d_model_id = Column(String(36), ForeignKey("vtuber_3d_models.id"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # 关系
    user = relationship("User", back_populates="characters")
    default_llm_model = relationship("LLMModel", foreign_keys=[default_llm_model_id], back_populates="characters")
    default_3d_model = relationship("VTuber3DModel", foreign_keys=[default_3d_model_id], back_populates="characters")
    voice_configs = relationship("VoiceConfig", back_populates="character", cascade="all, delete-orphan", order_by="VoiceConfig.priority")
    live_sessions = relationship("LiveSession", back_populates="character")


class VoiceConfig(Base):
    """声音配置表"""
    __tablename__ = "voice_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    character_id = Column(String(36), ForeignKey("characters.id"), nullable=False, index=True)
    voice_name = Column(String(50), nullable=False)  # Cherry, Serena等
    tts_model = Column(String(100), nullable=False)  # qwen3-tts-flash-realtime等
    is_default = Column(Boolean, default=False, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    character = relationship("Character", back_populates="voice_configs")
    live_sessions = relationship("LiveSession", back_populates="voice_config")


class LiveSession(Base):
    """直播会话表"""
    __tablename__ = "live_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    character_id = Column(String(36), ForeignKey("characters.id"), nullable=False)
    topic = Column(String(255), nullable=False)
    llm_model_id = Column(String(36), ForeignKey("llm_models.id"), nullable=False)
    voice_config_id = Column(String(36), ForeignKey("voice_configs.id"), nullable=False)
    vtuber_3d_model_id = Column(String(36), ForeignKey("vtuber_3d_models.id"))
    status = Column(Enum(SessionStatus), default=SessionStatus.PENDING, nullable=False)
    script_path = Column(String(255))
    audio_dir = Column(String(255))
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    session_metadata = Column("metadata", JSON, default=dict)  # 使用 session_metadata 作为属性名，metadata 作为列名
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="live_sessions")
    character = relationship("Character", back_populates="live_sessions")
    llm_model = relationship("LLMModel", back_populates="live_sessions")
    voice_config = relationship("VoiceConfig", back_populates="live_sessions")
    vtuber_3d_model = relationship("VTuber3DModel", back_populates="live_sessions")


class SystemSetting(Base):
    """系统配置表"""
    __tablename__ = "system_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text)
    category = Column(String(50), nullable=False, index=True)  # tts, llm, general
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
