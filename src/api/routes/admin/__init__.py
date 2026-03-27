"""
管理员后台 API 路由
"""

from .users import router as users_router
from .system import router as system_router
from .error_reports import router as error_reports_router

__all__ = [
    "users_router",
    "system_router",
    "error_reports_router",
]
