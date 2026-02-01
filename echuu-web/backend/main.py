"""ECHUU Web 后端主入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

try:
    # 作为包导入时使用相对导入
    from .config import SCRIPTS_DIR, CORS_ORIGINS, CORS_CREDENTIALS, CORS_METHODS, CORS_HEADERS, SERVER_HOST, SERVER_PORT
    from .routers import api, websocket, auth, characters, models, settings
    from .database.database import init_db
except ImportError:
    # 直接运行时使用绝对导入
    from config import SCRIPTS_DIR, CORS_ORIGINS, CORS_CREDENTIALS, CORS_METHODS, CORS_HEADERS, SERVER_HOST, SERVER_PORT
    from routers import api, websocket, auth, characters, models, settings
    from database.database import init_db

# 创建 FastAPI 应用
app = FastAPI(title="ECHUU Web 控制台 API")

# 初始化数据库
try:
    init_db()
    # 初始化默认数据
    try:
        try:
            from .migrations.init_data import init_default_data
        except ImportError:
            from migrations.init_data import init_default_data
        init_default_data()
    except Exception as e:
        print(f"⚠️ 初始化默认数据失败（可能已存在）: {e}")

except Exception as e:
    print(f"⚠️ 数据库初始化警告: {e}")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_CREDENTIALS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)

# 挂载静态资源
app.mount("/audio", StaticFiles(directory=str(SCRIPTS_DIR)), name="audio")

# 注册路由
app.include_router(websocket.router)
app.include_router(auth.router, prefix="/api")
app.include_router(characters.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(api.router, prefix="/api", tags=["api"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
