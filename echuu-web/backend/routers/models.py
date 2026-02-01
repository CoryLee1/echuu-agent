"""模型管理路由（AI模型和3D模型）"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import os

try:
    from ..auth.auth import get_current_active_user, get_current_admin_user
    from ..database.database import get_db
    from ..database.models import User, LLMModel, VTuber3DModel, LLMProvider
    from ..models import (
        LLMModelCreate,
        LLMModelResponse,
        VTuber3DModelCreate,
        VTuber3DModelResponse,
    )
    from ..config import PROJECT_ROOT
except ImportError:
    from auth.auth import get_current_active_user, get_current_admin_user
    from database.database import get_db
    from database.models import User, LLMModel, VTuber3DModel, LLMProvider
    from models import (
        LLMModelCreate,
        LLMModelResponse,
        VTuber3DModelCreate,
        VTuber3DModelResponse,
    )
    from config import PROJECT_ROOT

router = APIRouter(prefix="/models", tags=["模型管理"])

# 3D模型存储目录
MODELS_DIR = PROJECT_ROOT / "echuu-web" / "backend" / "storage" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ========== LLM模型管理 ==========

@router.get("/llm", response_model=List[LLMModelResponse])
async def list_llm_models(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取所有LLM模型"""
    models = db.query(LLMModel).all()
    return models


@router.get("/llm/{model_id}", response_model=LLMModelResponse)
async def get_llm_model(
    model_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取单个LLM模型"""
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    return model


@router.post("/llm", response_model=LLMModelResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_model(
    model_data: LLMModelCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """创建LLM模型（仅管理员）"""
    # 如果设置为默认，取消其他默认
    if model_data.is_default:
        db.query(LLMModel).filter(LLMModel.is_default == True).update({"is_default": False})
    
    model = LLMModel(
        name=model_data.name,
        provider=LLMProvider(model_data.provider),
        model_id=model_data.model_id,
        api_key_env=model_data.api_key_env,
        is_default=model_data.is_default,
        config=model_data.config,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.put("/llm/{model_id}", response_model=LLMModelResponse)
async def update_llm_model(
    model_id: str,
    model_data: LLMModelCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """更新LLM模型（仅管理员）"""
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    # 如果设置为默认，取消其他默认
    if model_data.is_default and not model.is_default:
        db.query(LLMModel).filter(LLMModel.is_default == True).update({"is_default": False})
    
    model.name = model_data.name
    model.provider = LLMProvider(model_data.provider)
    model.model_id = model_data.model_id
    model.api_key_env = model_data.api_key_env
    model.is_default = model_data.is_default
    model.config = model_data.config
    
    db.commit()
    db.refresh(model)
    return model


@router.delete("/llm/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_model(
    model_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """删除LLM模型（仅管理员）"""
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    db.delete(model)
    db.commit()
    return None


# ========== 3D模型管理 ==========

@router.get("/3d", response_model=List[VTuber3DModelResponse])
async def list_3d_models(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取所有3D模型"""
    models = db.query(VTuber3DModel).all()
    return models


@router.get("/3d/{model_id}", response_model=VTuber3DModelResponse)
async def get_3d_model(
    model_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取单个3D模型"""
    model = db.query(VTuber3DModel).filter(VTuber3DModel.id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    return model


@router.post("/3d", response_model=VTuber3DModelResponse, status_code=status.HTTP_201_CREATED)
async def create_3d_model(
    model_data: VTuber3DModelCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """创建3D模型（仅管理员）"""
    # 如果设置为默认，取消其他默认
    if model_data.is_default:
        db.query(VTuber3DModel).filter(VTuber3DModel.is_default == True).update({"is_default": False})
    
    model = VTuber3DModel(
        name=model_data.name,
        model_path=model_data.model_path,
        provider=model_data.provider,
        preview_image_url=model_data.preview_image_url,
        config=model_data.config,
        is_default=model_data.is_default,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.post("/3d/upload", response_model=VTuber3DModelResponse, status_code=status.HTTP_201_CREATED)
async def upload_3d_model(
    file: UploadFile = File(...),
    name: str = None,
    provider: str = "vrm",
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """上传3D模型文件（仅管理员）"""
    # 验证文件类型
    allowed_extensions = {".vrm", ".glb", ".gltf"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型，仅支持: {', '.join(allowed_extensions)}"
        )
    
    # 保存文件
    model_name = name or Path(file.filename).stem
    file_path = MODELS_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 创建数据库记录
    model = VTuber3DModel(
        name=model_name,
        model_path=str(file_path.relative_to(PROJECT_ROOT)),
        provider=provider,
        is_default=False,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.put("/3d/{model_id}", response_model=VTuber3DModelResponse)
async def update_3d_model(
    model_id: str,
    model_data: VTuber3DModelCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """更新3D模型（仅管理员）"""
    model = db.query(VTuber3DModel).filter(VTuber3DModel.id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    # 如果设置为默认，取消其他默认
    if model_data.is_default and not model.is_default:
        db.query(VTuber3DModel).filter(VTuber3DModel.is_default == True).update({"is_default": False})
    
    model.name = model_data.name
    model.model_path = model_data.model_path
    model.provider = model_data.provider
    model.preview_image_url = model_data.preview_image_url
    model.config = model_data.config
    model.is_default = model_data.is_default
    
    db.commit()
    db.refresh(model)
    return model


@router.delete("/3d/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_3d_model(
    model_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """删除3D模型（仅管理员）"""
    model = db.query(VTuber3DModel).filter(VTuber3DModel.id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    # 删除文件
    model_file_path = PROJECT_ROOT / model.model_path if not Path(model.model_path).is_absolute() else Path(model.model_path)
    if model_file_path.exists():
        os.remove(model_file_path)
    
    db.delete(model)
    db.commit()
    return None
