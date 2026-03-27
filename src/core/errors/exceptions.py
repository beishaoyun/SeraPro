"""
错误处理基础类
"""

from typing import Optional, Dict, Any
from .types import ErrorLevel, ErrorCategory, get_error_template


class SeraProError(Exception):
    """基础错误类"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        code: str,
        level: ErrorLevel = ErrorLevel.ERROR,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False,
        user_message: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.code = code
        self.level = level
        self.details = details or {}
        self.recoverable = recoverable
        self.user_message = user_message

        # 尝试从模板加载用户消息
        if not user_message:
            template = get_error_template(code)
            if template:
                self.user_message = template.user_message
                if not level:
                    self.level = template.level

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category.value,
            "level": self.level.value,
            "details": self.details,
            "recoverable": self.recoverable,
            "user_message": self.user_message,
        }


# 具体错误类型
class SSHConnectionError(SeraProError):
    """SSH 连接错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.DEPLOY_CONNECT_FAILED,
            code="DEPLOY_CONNECT_FAILED",
            details=details,
            recoverable=True
        )


class SSHAuthError(SeraProError):
    """SSH 认证错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.DEPLOY_AUTH_FAILED,
            code="DEPLOY_AUTH_FAILED",
            details=details,
            recoverable=False
        )


class CommandExecutionError(SeraProError):
    """命令执行错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.DEPLOY_EXEC_FAILED,
            code="DEPLOY_EXEC_FAILED",
            details=details,
            recoverable=True
        )


class TimeoutError(SeraProError):
    """超时错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.DEPLOY_TIMEOUT,
            code="DEPLOY_TIMEOUT",
            details=details,
            recoverable=True
        )


class DependencyNotFoundError(SeraProError):
    """依赖缺失错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.DEPLOY_EXEC_FAILED,
            code="DEPENDENCY_NOT_FOUND",
            details=details,
            recoverable=True
        )


class InsufficientResourcesError(SeraProError):
    """资源不足错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.SYSTEM_RESOURCE_ERROR,
            code="INSUFFICIENT_RESOURCES",
            details=details,
            recoverable=False
        )


class AIAPIError(SeraProError):
    """AI API 调用错误"""
    def __init__(self, message: str, provider: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.AI_API_ERROR,
            code="AI_API_ERROR",
            details={"provider": provider, **(details or {})},
            recoverable=True
        )


class AIRateLimitError(SeraProError):
    """AI 限流错误"""
    def __init__(self, message: str, provider: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.AI_RATE_LIMIT,
            code="AI_RATE_LIMIT",
            details={"provider": provider, **(details or {})},
            recoverable=True
        )


class DatabaseError(SeraProError):
    """数据库错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE_ERROR,
            code="DATABASE_ERROR",
            details=details,
            recoverable=False
        )


class PermissionDeniedError(SeraProError):
    """权限不足错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.USER_PERMISSION_ERROR,
            code="USER_PERMISSION_ERROR",
            details=details,
            recoverable=False
        )
