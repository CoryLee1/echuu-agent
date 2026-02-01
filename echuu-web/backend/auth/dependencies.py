"""认证依赖注入"""
from fastapi import Depends
from sqlalchemy.orm import Session

try:
    from ..auth.auth import get_current_user, get_current_active_user, get_current_admin_user
    from ..database.database import get_db
    from ..database.models import User
except ImportError:
    from auth.auth import get_current_user, get_current_active_user, get_current_admin_user
    from database.database import get_db
    from database.models import User

# 便捷依赖
CurrentUser = Depends(get_current_active_user)
CurrentAdmin = Depends(get_current_admin_user)
GetDB = Depends(get_db)
