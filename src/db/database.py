"""
数据库连接配置
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

from src.config import settings

logger = logging.getLogger(__name__)

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # 连接前测试
    echo=settings.DEBUG  # 开发环境打印 SQL
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()


def get_db() -> Session:
    """
    获取数据库会话依赖
    用于 FastAPI 依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Session:
    """
    获取数据库会话上下文管理器
    用于非 API 场景
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


def init_db():
    """初始化数据库 (创建所有表)"""
    from src.db.models import Base  # 导入所有模型
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


def drop_db():
    """删除所有表 (仅用于开发/测试)"""
    from src.db.models import Base
    Base.metadata.drop_all(bind=engine)
    logger.info("Database dropped")
