"""
管理员 - 用户管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.database import get_db
from src.db.models import User, UserRole, AuditLog, Server, Deployment
from src.api.routes.auth import get_current_user, hash_password

router = APIRouter(tags=["admin-users"])


def _check_admin(current_user: User):
    """检查是否为管理员"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    role: Optional[str] = None,
    status: Optional[str] = None,  # active, disabled
    search: Optional[str] = None,  # 搜索邮箱
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出所有用户（管理员专用）"""
    _check_admin(current_user)

    query = db.query(User)

    if role:
        query = query.filter(User.role == role)
    if status == "disabled":
        query = query.filter(User.is_disabled == True)
    elif status == "active":
        query = query.filter(User.is_disabled == False)
    if search:
        query = query.filter(User.email.ilike(f"%{search}%"))

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "role": u.role.value,
                "is_disabled": u.is_disabled,
                "created_at": u.created_at.isoformat(),
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None
            }
            for u in users
        ],
        "skip": skip,
        "limit": limit
    }


@router.get("/{user_id}")
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户详情（管理员专用）"""
    _check_admin(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 额外统计信息
    server_count = db.query(func.count(Server.id)).filter(Server.user_id == user_id).scalar()
    deployment_count = db.query(func.count(Deployment.id)).filter(Deployment.user_id == user_id).scalar()

    from src.core.ai.cost_tracker import AICostRecord
    total_cost = db.query(func.sum(AICostRecord.cost_cny)).filter(
        AICostRecord.user_id == user_id
    ).scalar() or 0

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role.value,
            "is_disabled": user.is_disabled,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
        },
        "stats": {
            "server_count": server_count,
            "deployment_count": deployment_count,
            "total_ai_cost_cny": round(total_cost, 4) if total_cost else 0
        }
    }


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重置用户密码（管理员专用）"""
    _check_admin(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_password = request.get("password")
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user.password_hash = hash_password(new_password)
    db.commit()

    # 记录审计日志
    AuditLog.create(
        db=db,
        user_id=current_user.id,
        action="ADMIN_RESET_USER_PASSWORD",
        resource_type="user",
        resource_id=user_id,
        details={"admin_id": current_user.id, "target_user_id": user_id}
    )

    return {"status": "success", "message": "Password reset"}


@router.post("/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """禁用/启用用户（管理员专用）"""
    _check_admin(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_disabled = request.get("disabled", True)
    db.commit()

    # 审计日志
    AuditLog.create(
        db=db,
        user_id=current_user.id,
        action="ADMIN_TOGGLE_USER_STATUS",
        resource_type="user",
        resource_id=user_id,
        details={"disabled": user.is_disabled}
    )

    return {"status": "success", "disabled": user.is_disabled}


@router.post("/{user_id}/set-role")
async def set_user_role(
    user_id: int,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """设置用户角色（管理员专用）"""
    _check_admin(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role_value = request.get("role")
    try:
        role = UserRole(role_value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role_value}")

    user.role = role
    db.commit()

    # 审计日志
    AuditLog.create(
        db=db,
        user_id=current_user.id,
        action="ADMIN_SET_USER_ROLE",
        resource_type="user",
        resource_id=user_id,
        details={"new_role": role.value}
    )

    return {"status": "success", "role": role.value}
