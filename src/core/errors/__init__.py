"""
错误处理模块
"""

from .types import (
    ErrorLevel,
    ErrorCategory,
    ErrorTemplate,
    ERROR_TEMPLATES,
    get_error_template,
    register_error_template,
)
from .exceptions import (
    SeraProError,
    SSHConnectionError,
    SSHAuthError,
    CommandExecutionError,
    TimeoutError,
    DependencyNotFoundError,
    InsufficientResourcesError,
    AIAPIError,
    AIRateLimitError,
    DatabaseError,
    PermissionDeniedError,
)

__all__ = [
    # Types
    "ErrorLevel",
    "ErrorCategory",
    "ErrorTemplate",
    "ERROR_TEMPLATES",
    "get_error_template",
    "register_error_template",
    # Exceptions
    "SeraProError",
    "SSHConnectionError",
    "SSHAuthError",
    "CommandExecutionError",
    "TimeoutError",
    "DependencyNotFoundError",
    "InsufficientResourcesError",
    "AIAPIError",
    "AIRateLimitError",
    "DatabaseError",
    "PermissionDeniedError",
]
