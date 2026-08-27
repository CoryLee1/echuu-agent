"""数据库连接和会话管理"""
import os
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 数据库路径
DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_DIR}/echuu.db")

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=os.getenv("DB_ECHO", "false").lower() == "true"
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()


def get_db():
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建表）"""
    Base.metadata.create_all(bind=engine)
    # create_all 不会为已存在的表补列。这几个归档字段都是可向后兼容的
    # additive migration，让旧 SQLite/Postgres 部署启动时也能安全升级。
    columns = {column["name"] for column in inspect(engine).get_columns("live_sessions")}
    additions = {
        "s3_prefix": "VARCHAR(512)",
        "uploaded_count": "INTEGER NOT NULL DEFAULT 0",
        "archive_status": "VARCHAR(32) NOT NULL DEFAULT 'pending'",
        "archive_error": "TEXT",
    }
    with engine.begin() as connection:
        for name, ddl in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE live_sessions ADD COLUMN {name} {ddl}"))
