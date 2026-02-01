"""角色管理路由"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

try:
    from ..auth.auth import get_current_active_user
    from ..database.database import get_db
    from ..database.models import User, Character, VoiceConfig
    from ..models import (
        CharacterCreate,
        CharacterUpdate,
        CharacterResponse,
        VoiceConfigCreate,
        VoiceConfigResponse,
    )
except ImportError:
    from auth.auth import get_current_active_user
    from database.database import get_db
    from database.models import User, Character, VoiceConfig
    from models import (
        CharacterCreate,
        CharacterUpdate,
        CharacterResponse,
        VoiceConfigCreate,
        VoiceConfigResponse,
    )

router = APIRouter(prefix="/characters", tags=["角色管理"])


@router.get("", response_model=List[CharacterResponse])
async def list_characters(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的所有角色"""
    characters = db.query(Character).filter(
        Character.user_id == current_user.id,
        Character.is_active == True
    ).all()
    return characters


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取单个角色详情"""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    
    return character


@router.post("", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    character_data: CharacterCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建角色"""
    # 检查角色名是否重复
    existing = db.query(Character).filter(
        Character.user_id == current_user.id,
        Character.name == character_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色名已存在"
        )
    
    # 创建角色
    character = Character(
        user_id=current_user.id,
        name=character_data.name,
        persona=character_data.persona,
        background=character_data.background,
        avatar_url=character_data.avatar_url,
        default_llm_model_id=character_data.default_llm_model_id,
        default_3d_model_id=character_data.default_3d_model_id,
    )
    db.add(character)
    db.flush()  # 获取character.id
    
    # 创建声音配置
    for voice_data in character_data.voice_configs:
        voice_config = VoiceConfig(
            character_id=character.id,
            voice_name=voice_data.voice_name,
            tts_model=voice_data.tts_model,
            is_default=voice_data.is_default,
            priority=voice_data.priority,
        )
        db.add(voice_config)
    
    # 如果设置了默认声音，确保只有一个默认
    if any(vc.is_default for vc in character_data.voice_configs):
        _ensure_single_default_voice(db, character.id)
    
    db.commit()
    db.refresh(character)
    return character


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    character_data: CharacterUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新角色"""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    
    # 更新字段
    update_data = character_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(character, field, value)
    
    db.commit()
    db.refresh(character)
    return character


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    character_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除角色（软删除）"""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    
    character.is_active = False
    db.commit()
    return None


# ========== 声音配置管理 ==========

@router.post("/{character_id}/voices", response_model=VoiceConfigResponse, status_code=status.HTTP_201_CREATED)
async def add_voice_config(
    character_id: str,
    voice_data: VoiceConfigCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """为角色添加声音配置"""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    
    # 检查声音名是否重复
    existing = db.query(VoiceConfig).filter(
        VoiceConfig.character_id == character_id,
        VoiceConfig.voice_name == voice_data.voice_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该声音配置已存在"
        )
    
    voice_config = VoiceConfig(
        character_id=character_id,
        voice_name=voice_data.voice_name,
        tts_model=voice_data.tts_model,
        is_default=voice_data.is_default,
        priority=voice_data.priority,
    )
    db.add(voice_config)
    
    # 如果设置为默认，确保只有一个默认
    if voice_data.is_default:
        _ensure_single_default_voice(db, character_id, exclude_id=voice_config.id)
    
    db.commit()
    db.refresh(voice_config)
    return voice_config


@router.put("/{character_id}/voices/{voice_id}", response_model=VoiceConfigResponse)
async def update_voice_config(
    character_id: str,
    voice_id: str,
    voice_data: VoiceConfigCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新声音配置"""
    # 验证角色所有权
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    
    voice_config = db.query(VoiceConfig).filter(
        VoiceConfig.id == voice_id,
        VoiceConfig.character_id == character_id
    ).first()
    
    if not voice_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="声音配置不存在"
        )
    
    # 更新字段
    voice_config.voice_name = voice_data.voice_name
    voice_config.tts_model = voice_data.tts_model
    voice_config.priority = voice_data.priority
    
    # 处理默认设置
    if voice_data.is_default and not voice_config.is_default:
        _ensure_single_default_voice(db, character_id, exclude_id=voice_id)
        voice_config.is_default = True
    elif not voice_data.is_default and voice_config.is_default:
        voice_config.is_default = False
    
    db.commit()
    db.refresh(voice_config)
    return voice_config


@router.delete("/{character_id}/voices/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice_config(
    character_id: str,
    voice_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除声音配置"""
    # 验证角色所有权
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )
    
    voice_config = db.query(VoiceConfig).filter(
        VoiceConfig.id == voice_id,
        VoiceConfig.character_id == character_id
    ).first()
    
    if not voice_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="声音配置不存在"
        )
    
    db.delete(voice_config)
    db.commit()
    return None


def _ensure_single_default_voice(db: Session, character_id: str, exclude_id: str = None):
    """确保角色只有一个默认声音"""
    query = db.query(VoiceConfig).filter(
        VoiceConfig.character_id == character_id,
        VoiceConfig.is_default == True
    )
    if exclude_id:
        query = query.filter(VoiceConfig.id != exclude_id)
    
    for voice in query.all():
        voice.is_default = False
