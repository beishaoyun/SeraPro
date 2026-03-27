"""
管理员 - 系统配置 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from src.db.database import get_db
from src.db.models import User, Server, Deployment, KnowledgeBase, AuditLog
from src.api.routes.auth import get_current_user
from src.core.ai.cost_tracker import AICostRecord

router = APIRouter(tags=["admin-system"])


def _check_admin(current_user: User):
    """检查是否为管理员"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


class SystemConfigUpdate(BaseModel):
    """系统配置更新"""
    # AI Provider 配置
    openai_api_key: str = Field(default="")
    openai_enabled: bool = Field(default=True)

    volcengine_api_key: str = Field(default="")
    volcengine_enabled: bool = Field(default=True)

    alibaba_api_key: str = Field(default="")
    alibaba_enabled: bool = Field(default=True)

    deepseek_api_key: str = Field(default="")
    deepseek_enabled: bool = Field(default=True)

    default_provider: str = Field(default="volcengine")
    default_model: str = Field(default="doubao-pro-32k")

    # 系统参数
    max_servers_per_user: int = Field(default=10, description="每用户最大服务器数")
    max_deployments_per_day: int = Field(default=50, description="每用户每日最大部署数")

    # 功能开关
    enable_registration: bool = Field(default=True, description="是否开放注册")
    enable_ai_debug: bool = Field(default=True, description="是否启用 AI 排错")

    # 配额
    free_tier_ai_budget_cny: float = Field(default=10.0, description="免费用户 AI 预算")


@router.get("/config")
async def get_system_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取系统配置（管理员专用）"""
    _check_admin(current_user)

    # 从环境变量或数据库读取配置
    # 这里简化实现，实际应该从数据库读取
    from src.config import get_settings
    settings = get_settings()

    return {
        "config": {
            "openai_enabled": True,
            "volcengine_enabled": True,
            "alibaba_enabled": True,
            "deepseek_enabled": True,
            "default_provider": "volcengine",
            "default_model": "doubao-pro-32k",
            "max_servers_per_user": 10,
            "max_deployments_per_day": 50,
            "enable_registration": True,
            "enable_ai_debug": True,
            "free_tier_ai_budget_cny": 10.0,
        }
    }


@router.put("/config")
async def update_system_config(
    config_data: SystemConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新系统配置（管理员专用）"""
    _check_admin(current_user)

    # 更新配置（实际应该写入数据库）
    # 这里简化实现

    # 审计日志
    AuditLog.create(
        db=db,
        user_id=current_user.id,
        action="ADMIN_UPDATE_SYSTEM_CONFIG",
        details={"updated_fields": list(config_data.dict().keys())}
    )

    return {"status": "success", "config": config_data.dict()}


@router.get("/stats")
async def get_system_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取系统统计（管理员专用）"""
    _check_admin(current_user)

    now = datetime.utcnow()

    stats = {
        "total_users": db.query(User).count(),
        "active_users_24h": db.query(User).filter(
            User.last_login_at >= now - timedelta(hours=24)
        ).count() if hasattr(User, 'last_login_at') else 0,
        "total_servers": db.query(Server).count(),
        "total_deployments": db.query(Deployment).count(),
        "deployments_success_24h": db.query(Deployment).filter(
            Deployment.status == "success",
            Deployment.updated_at >= now - timedelta(hours=24)
        ).count(),
        "deployments_failed_24h": db.query(Deployment).filter(
            Deployment.status == "failed",
            Deployment.updated_at >= now - timedelta(hours=24)
        ).count(),
        "total_knowledge_entries": db.query(KnowledgeBase).count(),
        "ai_cost_total_today": db.query(func.sum(AICostRecord.cost_cny)).filter(
            AICostRecord.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
        ).scalar() or 0,
    }

    # 计算成功率
    total_24h = stats["deployments_success_24h"] + stats["deployments_failed_24h"]
    stats["success_rate_24h"] = round(
        stats["deployments_success_24h"] / total_24h * 100, 2
    ) if total_24h > 0 else 0

    return {"stats": stats}


@router.get("/audit-logs")
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出审计日志（管理员专用）"""
    _check_admin(current_user)

    logs = db.query(AuditLog).order_by(
        AuditLog.created_at.desc()
    ).offset(skip).limit(limit).all()

    total = db.query(AuditLog).count()

    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "ip_address": log.ip_address,
                "details": log.details,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ],
        "skip": skip,
        "limit": limit
    }
