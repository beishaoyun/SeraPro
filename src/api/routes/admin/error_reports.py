"""
管理员 - 错误统计报表 API
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, Date

from src.db.database import get_db
from src.db.models import Deployment, DeploymentStep, Server
from src.api.routes.auth import get_current_user
from src.db.models import User

router = APIRouter(tags=["admin-errors"])


def _check_admin(current_user: User):
    """检查是否为管理员"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/summary")
async def get_error_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """错误摘要统计（管理员专用）"""
    _check_admin(current_user)

    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=7)
    if not end_date:
        end_date = datetime.utcnow()

    # 按错误类型统计
    error_stats = db.query(
        DeploymentStep.error_message,
        func.count().label("count")
    ).filter(
        DeploymentStep.status == "failed",
        DeploymentStep.created_at >= start_date,
        DeploymentStep.created_at <= end_date
    ).group_by(
        DeploymentStep.error_message
    ).order_by(desc("count")).limit(20).all()

    # 按服务类型统计
    service_type_stats = db.query(
        Deployment.service_type,
        func.count().label("count")
    ).filter(
        Deployment.status == "failed",
        Deployment.updated_at >= start_date,
        Deployment.updated_at <= end_date
    ).group_by(Deployment.service_type).all()

    # 按操作系统统计
    os_stats = db.query(
        Server.os_type,
        Server.os_version,
        func.count().label("count")
    ).join(Deployment).filter(
        Deployment.status == "failed",
        Deployment.updated_at >= start_date,
        Deployment.updated_at <= end_date
    ).group_by(Server.os_type, Server.os_version).all()

    # 总错误数
    total_errors = db.query(func.count(Deployment.id)).filter(
        Deployment.status == "failed",
        Deployment.updated_at >= start_date,
        Deployment.updated_at <= end_date
    ).scalar()

    # 总部署数
    total_deployments = db.query(func.count(Deployment.id)).filter(
        Deployment.updated_at >= start_date,
        Deployment.updated_at <= end_date
    ).scalar()

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "total_errors": total_errors,
        "total_deployments": total_deployments,
        "error_rate": round(total_errors / total_deployments * 100, 2) if total_deployments > 0 else 0,
        "by_error_type": [
            {"error": s.error_message[:100] if s.error_message else "Unknown", "count": s.count}
            for s in error_stats
        ],
        "by_service_type": [
            {"type": s.service_type or "unknown", "count": s.count}
            for s in service_type_stats
        ],
        "by_os": [
            {"os": f"{s.os_type} {s.os_version}", "count": s.count}
            for s in os_stats
        ]
    }


@router.get("/trend")
async def get_error_trend(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """错误趋势图（管理员专用）"""
    _check_admin(current_user)

    start_date = datetime.utcnow() - timedelta(days=days)

    # 按天统计错误数
    trend = db.query(
        func.date_trunc("day", DeploymentStep.created_at).label("date"),
        func.count().label("count")
    ).filter(
        DeploymentStep.status == "failed",
        DeploymentStep.created_at >= start_date
    ).group_by("date").order_by("date").all()

    # 按天统计成功率
    from sqlalchemy import case
    deployment_stats = db.query(
        func.date_trunc("day", Deployment.created_at).label("date"),
        func.sum(case((Deployment.status == "success", 1), else_=0)).label("success"),
        func.sum(case((Deployment.status == "failed", 1), else_=0)).label("failed"),
        func.count().label("total")
    ).filter(
        Deployment.created_at >= start_date
    ).group_by("date").order_by("date").all()

    return {
        "error_trend": [
            {"date": t.date.strftime("%Y-%m-%d"), "count": t.count}
            for t in trend
        ],
        "deployment_stats": [
            {
                "date": s.date.strftime("%Y-%m-%d"),
                "success": s.success or 0,
                "failed": s.failed or 0,
                "total": s.total,
                "success_rate": round((s.success or 0) / s.total * 100, 2) if s.total > 0 else 0
            }
            for s in deployment_stats
        ]
    }


@router.get("/top-projects")
async def get_top_failed_projects(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取失败率最高的项目（管理员专用）"""
    _check_admin(current_user)

    # 按 GitHub 项目统计失败率
    projects = db.query(
        Deployment.github_url,
        func.count().label("total"),
        func.sum(func.case((Deployment.status == "failed", 1), else_=0)).label("failed"),
    ).group_by(Deployment.github_url).having(
        func.count() >= 5  # 至少 5 次部署
    ).all()

    # 计算失败率并排序
    result = []
    for p in projects:
        failure_rate = (p.failed / p.total * 100) if p.total > 0 else 0
        result.append({
            "github_url": p.github_url,
            "total_deployments": p.total,
            "failed_deployments": p.failed,
            "failure_rate": round(failure_rate, 2)
        })

    result.sort(key=lambda x: x["failure_rate"], reverse=True)

    return {"projects": result[:limit]}


@router.get("/recent-errors")
async def get_recent_errors(
    limit: int = Query(20, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """最近错误列表（管理员专用）"""
    _check_admin(current_user)

    errors = db.query(
        DeploymentStep,
        Deployment,
        Server,
        User
    ).join(
        Deployment, DeploymentStep.deployment_id == Deployment.id
    ).join(
        Server, Deployment.server_id == Server.id
    ).join(
        User, Deployment.user_id == User.id
    ).filter(
        DeploymentStep.status == "failed"
    ).order_by(
        desc(DeploymentStep.created_at)
    ).limit(limit).all()

    return {
        "errors": [
            {
                "step_id": e.DeploymentStep.id,
                "deployment_id": e.Deployment.id,
                "error_message": e.DeploymentStep.error_message,
                "command": e.DeploymentStep.command,
                "step_number": e.DeploymentStep.step_number,
                "github_url": e.Deployment.github_url,
                "server_name": e.Server.name,
                "server_os": f"{e.Server.os_type} {e.Server.os_version}",
                "user_email": e.User.email,
                "created_at": e.DeploymentStep.created_at.isoformat()
            }
            for e in errors
        ]
    }
