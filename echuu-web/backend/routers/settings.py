"""系统设置路由"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

try:
    from ..auth.auth import get_current_admin_user
    from ..database.database import get_db
    from ..database.models import User, SystemSetting
    from ..models import SystemSettingCreate, SystemSettingResponse
except ImportError:
    from auth.auth import get_current_admin_user
    from database.database import get_db
    from database.models import User, SystemSetting
    from models import SystemSettingCreate, SystemSettingResponse

router = APIRouter(prefix="/settings", tags=["系统设置"])


@router.get("", response_model=List[SystemSettingResponse])
async def list_settings(
    category: str = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取系统设置（仅管理员）"""
    query = db.query(SystemSetting)
    if category:
        query = query.filter(SystemSetting.category == category)
    settings = query.all()
    return settings


@router.get("/{key}", response_model=SystemSettingResponse)
async def get_setting(
    key: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取单个设置项（仅管理员）"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设置项不存在"
        )
    return setting


@router.post("", response_model=SystemSettingResponse, status_code=status.HTTP_201_CREATED)
async def create_setting(
    setting_data: SystemSettingCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """创建系统设置（仅管理员）"""
    # 检查key是否已存在
    existing = db.query(SystemSetting).filter(SystemSetting.key == setting_data.key).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="设置项已存在"
        )
    
    setting = SystemSetting(
        key=setting_data.key,
        value=setting_data.value,
        category=setting_data.category,
        description=setting_data.description,
    )
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


@router.put("/{key}", response_model=SystemSettingResponse)
async def update_setting(
    key: str,
    value: str,
    description: str = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """更新系统设置（仅管理员）"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设置项不存在"
        )
    
    setting.value = value
    if description is not None:
        setting.description = description
    
    db.commit()
    db.refresh(setting)
    return setting


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    key: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """删除系统设置（仅管理员）"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设置项不存在"
        )
    
    db.delete(setting)
    db.commit()
    return None
