"""后端配置"""
import os
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# 脚本输出目录
SCRIPTS_DIR = PROJECT_ROOT / "output" / "scripts"
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# CORS 配置
CORS_ORIGINS = ["*"]
CORS_CREDENTIALS = True
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# 服务器配置
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# 数据库配置
DB_DIR = PROJECT_ROOT / "echuu-web" / "backend" / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_DIR / 'echuu.db'}")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天
