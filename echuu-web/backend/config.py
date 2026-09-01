"""后端配置"""
import os
from pathlib import Path

# 项目根目录 (still used for SCRIPTS_DIR / DB_DIR below)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 脚本输出目录
SCRIPTS_DIR = PROJECT_ROOT / "output" / "scripts"
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# CORS 配置。allow_origins=["*"] 配 allow_credentials=True 时，
# 预检不会回 Access-Control-Allow-Origin，浏览器会直接拦。
_DEFAULT_CORS_ORIGINS = [
    "https://echuu.live",
    "https://www.echuu.live",
    "https://echuu.xyz",
    "https://echuu-corylee1s-projects.vercel.app",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]
_extra_cors = [item.strip() for item in os.getenv("BACKEND_CORS_ORIGINS", "").split(",") if item.strip()]
CORS_ORIGINS = list(dict.fromkeys([*_DEFAULT_CORS_ORIGINS, *_extra_cors]))
CORS_ORIGIN_REGEX = os.getenv(
    "BACKEND_CORS_ORIGIN_REGEX",
    r"https://([a-z0-9-]+\.)*(echuu\.live|echuu\.xyz|vercel\.app)",
)
CORS_CREDENTIALS = True
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# 服务器配置
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# 数据库配置
DB_DIR = PROJECT_ROOT / "echuu-web" / "backend" / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DIARY_COVERS_DIR = DB_DIR / "diary-covers"
DIARY_COVERS_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_DIR / 'echuu.db'}")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天
