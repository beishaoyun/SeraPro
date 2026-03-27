"""
Pytest 配置文件
"""

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.db.database import Base, get_db
from src.api.main import app
from src.config import settings


# 测试数据库配置 - 使用 SQLite 进行测试
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite:///test.db"
)


@pytest.fixture(scope="session")
def engine():
    """创建数据库引擎"""
    return create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}  # SQLite 需要
    )


@pytest.fixture(scope="function")
def db_session(engine):
    """创建数据库 session"""
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session):
    """创建测试用户"""
    from src.db.models import User
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user = User(
        email="test@example.com",
        password_hash=pwd_context.hash("testpassword123"),
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture(scope="function")
def test_admin(db_session):
    """创建测试管理员"""
    from src.db.models import User
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    admin = User(
        email="admin@example.com",
        password_hash=pwd_context.hash("adminpass123"),
        role="admin"
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    yield admin
    db_session.delete(admin)
    db_session.commit()


@pytest.fixture(scope="function")
def auth_token(client, test_user):
    """获取认证令牌"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def admin_token(client, test_admin):
    """获取管理员令牌"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass123"}
    )
    return response.json()["access_token"]
