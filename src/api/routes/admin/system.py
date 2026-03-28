"""
管理员 - 系统配置 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import json

from src.db.database import get_db
from src.db.models import User, Server, Deployment, KnowledgeBase, AuditLog, SystemConfig
from src.api.routes.auth import get_current_user
from src.core.ai.cost_tracker import AICostRecord

router = APIRouter(tags=["admin-system"])


def _check_admin(current_user: User):
    """检查是否为管理员"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def _get_config_value(db: Session, key: str, default: str = "") -> str:
    """获取配置值"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    return config.config_value if config else default


def _set_config_value(db: Session, key: str, value: str, description: str = None):
    """设置配置值"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    if config:
        config.config_value = value
        if description:
            config.description = description
    else:
        config = SystemConfig(
            config_key=key,
            config_value=value,
            description=description
        )
        db.add(config)
    db.commit()


class SystemConfigResponse(BaseModel):
    """系统配置响应"""
    # AI Provider 配置
    openai_api_key: str = ""
    openai_enabled: bool = True
    openai_model: str = "gpt-4o-mini"

    volcengine_api_key: str = ""
    volcengine_enabled: bool = True
    volcengine_model: str = "doubao-pro-32k"

    alibaba_api_key: str = ""
    alibaba_enabled: bool = True
    alibaba_model: str = "qwen-plus"

    deepseek_api_key: str = ""
    deepseek_enabled: bool = True
    deepseek_model: str = "deepseek-chat"

    # Provider 选择
    ai_provider: str = "auto"  # auto, openai, volcengine, alibaba, deepseek
    default_model: str = "doubao-pro-32k"

    # 系统参数
    max_servers_per_user: int = 10
    max_deployments_per_day: int = 50
    enable_registration: bool = True
    enable_ai_debug: bool = True
    free_tier_ai_budget_cny: float = 10.0


class SystemConfigUpdate(BaseModel):
    """系统配置更新"""
    # AI Provider 配置
    openai_api_key: Optional[str] = None
    openai_enabled: Optional[bool] = None
    openai_model: Optional[str] = None

    volcengine_api_key: Optional[str] = None
    volcengine_enabled: Optional[bool] = None
    volcengine_model: Optional[str] = None

    alibaba_api_key: Optional[str] = None
    alibaba_enabled: Optional[bool] = None
    alibaba_model: Optional[str] = None

    deepseek_api_key: Optional[str] = None
    deepseek_enabled: Optional[bool] = None
    deepseek_model: Optional[str] = None

    # Provider 选择
    ai_provider: Optional[str] = None
    default_model: Optional[str] = None

    # 系统参数
    max_servers_per_user: Optional[int] = None
    max_deployments_per_day: Optional[int] = None
    enable_registration: Optional[bool] = None
    enable_ai_debug: Optional[bool] = None
    free_tier_ai_budget_cny: Optional[float] = None


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取系统配置（管理员专用）"""
    _check_admin(current_user)

    # 从数据库读取配置
    config = SystemConfigResponse(
        openai_api_key=_get_config_value(db, "openai_api_key", ""),
        openai_enabled=_get_config_value(db, "openai_enabled", "true") == "true",
        openai_model=_get_config_value(db, "openai_model", "gpt-4o-mini"),

        volcengine_api_key=_get_config_value(db, "volcengine_api_key", ""),
        volcengine_enabled=_get_config_value(db, "volcengine_enabled", "true") == "true",
        volcengine_model=_get_config_value(db, "volcengine_model", "doubao-pro-32k"),

        alibaba_api_key=_get_config_value(db, "alibaba_api_key", ""),
        alibaba_enabled=_get_config_value(db, "alibaba_enabled", "true") == "true",
        alibaba_model=_get_config_value(db, "alibaba_model", "qwen-plus"),

        deepseek_api_key=_get_config_value(db, "deepseek_api_key", ""),
        deepseek_enabled=_get_config_value(db, "deepseek_enabled", "true") == "true",
        deepseek_model=_get_config_value(db, "deepseek_model", "deepseek-chat"),

        ai_provider=_get_config_value(db, "ai_provider", "auto"),
        default_model=_get_config_value(db, "default_model", "doubao-pro-32k"),

        max_servers_per_user=int(_get_config_value(db, "max_servers_per_user", "10")),
        max_deployments_per_day=int(_get_config_value(db, "max_deployments_per_day", "50")),
        enable_registration=_get_config_value(db, "enable_registration", "true") == "true",
        enable_ai_debug=_get_config_value(db, "enable_ai_debug", "true") == "true",
        free_tier_ai_budget_cny=float(_get_config_value(db, "free_tier_ai_budget_cny", "10.0")),
    )

    return {"config": config}


@router.put("/config", response_model=Dict[str, Any])
async def update_system_config(
    config_data: SystemConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新系统配置（管理员专用）"""
    _check_admin(current_user)

    updated_fields = []

    # AI Provider 配置
    if config_data.openai_api_key is not None:
        _set_config_value(db, "openai_api_key", config_data.openai_api_key, "OpenAI API Key")
        updated_fields.append("openai_api_key")

    if config_data.openai_enabled is not None:
        _set_config_value(db, "openai_enabled", str(config_data.openai_enabled).lower(), "OpenAI 是否启用")
        updated_fields.append("openai_enabled")

    if config_data.openai_model is not None:
        _set_config_value(db, "openai_model", config_data.openai_model, "OpenAI 模型")
        updated_fields.append("openai_model")

    if config_data.volcengine_api_key is not None:
        _set_config_value(db, "volcengine_api_key", config_data.volcengine_api_key, "火山引擎 API Key")
        updated_fields.append("volcengine_api_key")

    if config_data.volcengine_enabled is not None:
        _set_config_value(db, "volcengine_enabled", str(config_data.volcengine_enabled).lower(), "火山引擎是否启用")
        updated_fields.append("volcengine_enabled")

    if config_data.volcengine_model is not None:
        _set_config_value(db, "volcengine_model", config_data.volcengine_model, "火山引擎模型")
        updated_fields.append("volcengine_model")

    if config_data.alibaba_api_key is not None:
        _set_config_value(db, "alibaba_api_key", config_data.alibaba_api_key, "阿里云 API Key")
        updated_fields.append("alibaba_api_key")

    if config_data.alibaba_enabled is not None:
        _set_config_value(db, "alibaba_enabled", str(config_data.alibaba_enabled).lower(), "阿里云是否启用")
        updated_fields.append("alibaba_enabled")

    if config_data.alibaba_model is not None:
        _set_config_value(db, "alibaba_model", config_data.alibaba_model, "阿里云模型")
        updated_fields.append("alibaba_model")

    if config_data.deepseek_api_key is not None:
        _set_config_value(db, "deepseek_api_key", config_data.deepseek_api_key, "DeepSeek API Key")
        updated_fields.append("deepseek_api_key")

    if config_data.deepseek_enabled is not None:
        _set_config_value(db, "deepseek_enabled", str(config_data.deepseek_enabled).lower(), "DeepSeek 是否启用")
        updated_fields.append("deepseek_enabled")

    if config_data.deepseek_model is not None:
        _set_config_value(db, "deepseek_model", config_data.deepseek_model, "DeepSeek 模型")
        updated_fields.append("deepseek_model")

    if config_data.ai_provider is not None:
        _set_config_value(db, "ai_provider", config_data.ai_provider, "AI Provider 选择")
        updated_fields.append("ai_provider")

    if config_data.default_model is not None:
        _set_config_value(db, "default_model", config_data.default_model, "默认模型")
        updated_fields.append("default_model")

    if config_data.max_servers_per_user is not None:
        _set_config_value(db, "max_servers_per_user", str(config_data.max_servers_per_user), "每用户最大服务器数")
        updated_fields.append("max_servers_per_user")

    if config_data.max_deployments_per_day is not None:
        _set_config_value(db, "max_deployments_per_day", str(config_data.max_deployments_per_day), "每用户每日最大部署数")
        updated_fields.append("max_deployments_per_day")

    if config_data.enable_registration is not None:
        _set_config_value(db, "enable_registration", str(config_data.enable_registration).lower(), "是否开放注册")
        updated_fields.append("enable_registration")

    if config_data.enable_ai_debug is not None:
        _set_config_value(db, "enable_ai_debug", str(config_data.enable_ai_debug).lower(), "是否启用 AI 排错")
        updated_fields.append("enable_ai_debug")

    if config_data.free_tier_ai_budget_cny is not None:
        _set_config_value(db, "free_tier_ai_budget_cny", str(config_data.free_tier_ai_budget_cny), "免费用户 AI 预算")
        updated_fields.append("free_tier_ai_budget_cny")

    # 审计日志
    AuditLog.create(
        db=db,
        user_id=current_user.id,
        action="ADMIN_UPDATE_SYSTEM_CONFIG",
        details={"updated_fields": updated_fields}
    )

    return {"status": "success", "message": "配置已保存", "updated_fields": updated_fields}


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
