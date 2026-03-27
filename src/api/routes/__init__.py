"""
API 路由模块
"""

from .auth import router as auth_router
from .servers import router as servers_router
from .deployments import router as deployments_router
from .knowledge import router as knowledge_router

__all__ = [
    "auth_router",
    "servers_router",
    "deployments_router",
    "knowledge_router",
]
