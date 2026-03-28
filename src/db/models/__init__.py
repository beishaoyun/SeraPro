"""
数据库模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

try:
    from .database import Base
except ImportError:
    from src.db.database import Base


class UserRole(str, enum.Enum):
    """用户角色"""
    USER = "user"
    ADMIN = "admin"


class ServerStatus(str, enum.Enum):
    """服务器状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class DeploymentStatus(str, enum.Enum):
    """部署状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.USER)
    is_disabled = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    servers = relationship("Server", back_populates="user", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")


class Server(Base):
    """服务器模型"""
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=22)
    auth_type = Column(String(50), nullable=False)  # password, ssh_key
    credentials = Column(Text, nullable=False)  # 加密存储的凭证
    os_type = Column(String(50), nullable=False)
    os_version = Column(String(50), nullable=False)
    status = Column(SQLEnum(ServerStatus, values_callable=lambda x: [e.value for e in x]), default=ServerStatus.ACTIVE)
    last_connected_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="servers")
    deployments = relationship("Deployment", back_populates="server")


class Deployment(Base):
    """部署模型"""
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False, index=True)
    github_url = Column(String(500), nullable=False)
    github_repo_name = Column(String(255), nullable=True)
    service_type = Column(String(50), nullable=True)
    status = Column(SQLEnum(DeploymentStatus, values_callable=lambda x: [e.value for e in x]), default=DeploymentStatus.PENDING)
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer)
    error_log = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="deployments")
    server = relationship("Server", back_populates="deployments")
    steps = relationship("DeploymentStep", back_populates="deployment", cascade="all, delete-orphan")


class DeploymentStep(Base):
    """部署步骤模型"""
    __tablename__ = "deployment_steps"

    id = Column(Integer, primary_key=True, index=True)
    deployment_id = Column(Integer, ForeignKey("deployments.id"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    description = Column(String(500), nullable=False)
    command = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)  # pending, running, success, failed, skipped
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    deployment = relationship("Deployment", back_populates="steps")


class KnowledgeBase(Base):
    """知识库模型 (使用 Pgvector)"""
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, index=True)
    github_url_hash = Column(String(64), unique=True, nullable=False)
    github_url = Column(Text, nullable=False)
    os_type = Column(String(50), nullable=False)
    os_version = Column(String(50), nullable=False)
    service_type = Column(String(50), nullable=False)
    deploy_steps = Column(JSON, nullable=False, default=list)
    common_errors = Column(JSON, nullable=False, default=list)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    """审计日志模型"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 关系
    user = relationship("User", back_populates="audit_logs")

    @classmethod
    def create(cls, db, user_id: int, action: str, **kwargs):
        """创建审计日志"""
        log = cls(
            user_id=user_id,
            action=action,
            **kwargs
        )
        db.add(log)
        db.commit()
        return log


class SystemConfig(Base):
    """系统配置模型"""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


__all__ = [
    "Base",
    "User",
    "Server",
    "Deployment",
    "DeploymentStep",
    "KnowledgeBase",
    "AuditLog",
    "SystemConfig",
    "UserRole",
    "ServerStatus",
    "DeploymentStatus",
]
