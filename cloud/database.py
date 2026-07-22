"""数据库连接配置 —— SQLAlchemy + PyMySQL

数据库引擎和会话工厂延迟创建，避免 Alembic env.py 在 import 时就尝试连接数据库。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from cloud.config import CloudSettings

settings = CloudSettings()

DATABASE_URL = (
    f"mysql+pymysql://{settings.db_user}:{settings.db_pass}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}?charset=utf8mb4"
)

Base = declarative_base()

# 引擎和会话工厂延迟创建（首次调用 get_db 时才初始化）
_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_recycle=3600)
    return _engine


def _get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


def get_db():
    """FastAPI 依赖注入用"""
    db = _get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
