"""
错误类型和级别定义
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ErrorLevel(str, Enum):
    """错误级别"""
    INFO = "info"           # 信息提示
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 严重错误


class ErrorCategory(str, Enum):
    """错误分类"""
    # 平台错误
    AI_API_ERROR = "ai_api_error"           # AI API 调用失败
    AI_RATE_LIMIT = "ai_rate_limit"         # AI 限流
    AI_TIMEOUT = "ai_timeout"               # AI 超时
    DATABASE_ERROR = "database_error"       # 数据库错误
    REDIS_ERROR = "redis_error"             # Redis 错误

    # 部署错误
    DEPLOY_CONNECT_FAILED = "deploy_connect_failed"     # SSH 连接失败
    DEPLOY_AUTH_FAILED = "deploy_auth_failed"           # SSH 认证失败
    DEPLOY_EXEC_FAILED = "deploy_exec_failed"           # 命令执行失败
    DEPLOY_TIMEOUT = "deploy_timeout"                   # 部署超时
    DEPLOY_ROLLBACK_FAILED = "deploy_rollback_failed"   # 回滚失败

    # 用户错误
    USER_INPUT_ERROR = "user_input_error"       # 用户输入错误
    USER_PERMISSION_ERROR = "user_permission_error"  # 权限不足

    # 系统错误
    SYSTEM_INTERNAL_ERROR = "system_internal_error"  # 内部错误
    SYSTEM_RESOURCE_ERROR = "system_resource_error"  # 资源不足


class ErrorTemplate(BaseModel):
    """错误模板"""
    code: str
    level: ErrorLevel
    category: ErrorCategory
    title: str           # 错误标题 (简短描述)
    message: str         # 错误详情 (支持模板变量)
    user_message: str    # 给用户看的消息 (友好提示)
    suggested_action: str  # 建议操作
    auto_retry: bool = False  # 是否自动重试
    notify_admin: bool = False  # 是否通知管理员


# 错误模板注册表
ERROR_TEMPLATES: Dict[str, ErrorTemplate] = {
    "AI_API_ERROR": ErrorTemplate(
        code="AI_API_ERROR",
        level=ErrorLevel.ERROR,
        category=ErrorCategory.AI_API_ERROR,
        title="AI 服务调用失败",
        message="调用 {provider} API 失败：{error_message}",
        user_message="AI 服务暂时不可用，我们正在尝试修复。请稍后重试。",
        suggested_action="检查 AI Provider 配置，确认 API Key 有效",
        auto_retry=True,
        notify_admin=True
    ),

    "AI_RATE_LIMIT": ErrorTemplate(
        code="AI_RATE_LIMIT",
        level=ErrorLevel.WARNING,
        category=ErrorCategory.AI_RATE_LIMIT,
        title="AI 服务限流",
        message="AI 服务请求频率过高：{provider}",
        user_message="系统繁忙，请稍后重试。",
        suggested_action="等待后重试",
        auto_retry=True,
        notify_admin=False
    ),

    "AI_TIMEOUT": ErrorTemplate(
        code="AI_TIMEOUT",
        level=ErrorLevel.ERROR,
        category=ErrorCategory.AI_TIMEOUT,
        title="AI 服务超时",
        message="AI 服务响应超时：{provider}, 超时时间：{timeout}s",
        user_message="AI 服务响应超时，正在重试...",
        suggested_action="等待后重试",
        auto_retry=True,
        notify_admin=False
    ),

    "DEPLOY_CONNECT_FAILED": ErrorTemplate(
        code="DEPLOY_CONNECT_FAILED",
        level=ErrorLevel.ERROR,
        category=ErrorCategory.DEPLOY_CONNECT_FAILED,
        title="服务器连接失败",
        message="无法连接到服务器：{server_host}:{server_port}, 错误：{error_message}",
        user_message="无法连接到您的服务器，请检查：1. 服务器 IP 是否正确 2. 服务器是否正常运行 3. 网络是否畅通",
        suggested_action="检查服务器状态和网络连接",
        auto_retry=False,
        notify_admin=False
    ),

    "DEPLOY_AUTH_FAILED": ErrorTemplate(
        code="DEPLOY_AUTH_FAILED",
        level=ErrorLevel.ERROR,
        category=ErrorCategory.DEPLOY_AUTH_FAILED,
        title="服务器认证失败",
        message="SSH 认证失败：服务器 {server_host}，错误：{error_message}",
        user_message="无法连接到您的服务器，请检查：1. SSH 密码/密钥是否正确 2. 服务器是否正常运行",
        suggested_action="更新服务器凭证后重试",
        auto_retry=False,
        notify_admin=False
    ),

    "DEPLOY_EXEC_FAILED": ErrorTemplate(
        code="DEPLOY_EXEC_FAILED",
        level=ErrorLevel.ERROR,
        category=ErrorCategory.DEPLOY_EXEC_FAILED,
        title="命令执行失败",
        message="步骤 {step_number} 执行失败：{command}，错误：{error_message}",
        user_message="部署过程中遇到错误，AI 正在分析原因并提供修复建议。",
        suggested_action="查看 AI 排错建议，确认后继续",
        auto_retry=False,
        notify_admin=False
    ),

    "DEPLOY_TIMEOUT": ErrorTemplate(
        code="DEPLOY_TIMEOUT",
        level=ErrorLevel.ERROR,
        category=ErrorCategory.DEPLOY_TIMEOUT,
        title="部署超时",
        message="部署步骤超时：步骤 {step_number}，命令：{command}，超时时间：{timeout}s",
        user_message="部署操作超时，请检查服务器状态",
        suggested_action="检查服务器负载和网络连接",
        auto_retry=True,
        notify_admin=False
    ),

    "DATABASE_ERROR": ErrorTemplate(
        code="DATABASE_ERROR",
        level=ErrorLevel.CRITICAL,
        category=ErrorCategory.DATABASE_ERROR,
        title="数据库错误",
        message="数据库操作失败：{error_message}",
        user_message="系统内部错误，请稍后重试。",
        suggested_action="检查数据库连接和状态",
        auto_retry=False,
        notify_admin=True
    ),

    "SYSTEM_INTERNAL_ERROR": ErrorTemplate(
        code="SYSTEM_INTERNAL_ERROR",
        level=ErrorLevel.CRITICAL,
        category=ErrorCategory.SYSTEM_INTERNAL_ERROR,
        title="系统内部错误",
        message="系统内部错误：{error_message}",
        user_message="系统内部错误，请联系管理员。",
        suggested_action="联系系统管理员",
        auto_retry=False,
        notify_admin=True
    ),
}


def get_error_template(code: str) -> Optional[ErrorTemplate]:
    """获取错误模板"""
    return ERROR_TEMPLATES.get(code)


def register_error_template(template: ErrorTemplate):
    """注册错误模板"""
    ERROR_TEMPLATES[template.code] = template
