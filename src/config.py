"""
应用配置管理
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 应用信息
    APP_NAME: str = "SerPro"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_URL: str = "postgresql://serapro:serapro_secret@localhost:5432/serapro"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PREFIX: str = "serapro:"

    # 安全配置
    SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 凭证加密主密钥 (应该是 32 字节)
    MASTER_KEY: str = "0123456789abcdef0123456789abcdef"

    # OpenAI 配置
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_BASE_URL: Optional[str] = None

    # 火山引擎 (豆包) 配置
    VOLCENGINE_API_KEY: str = ""
    VOLCENGINE_MODEL: str = ""

    # 阿里云 (通义千问) 配置
    ALIBABA_API_KEY: str = ""
    ALIBABA_MODEL: str = ""

    # DeepSeek 配置
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = ""

    # AI Provider 选择 (openai, volcengine, alibaba, deepseek, auto)
    AI_PROVIDER: str = "auto"

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # 限流配置
    RATE_LIMIT_PER_MINUTE: int = 100

    # 邮件通知 (SMTP)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # 短信通知
    SMS_PROVIDER: str = "aliyun"
    SMS_API_KEY: str = ""
    SMS_SECRET: str = ""

    # 钉钉通知
    DINGTALK_WEBHOOK_URL: str = ""
    DINGTALK_SECRET: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略未定义的字段


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings
