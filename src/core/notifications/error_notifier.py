"""
错误通知系统 - 多渠道告警
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """通知渠道"""
    EMAIL = "email"
    SMS = "sms"
    DINGTALK = "dingtalk"
    WEBHOOK = "webhook"
    INTERNAL = "internal"  # 站内消息


class NotificationConfig(BaseModel):
    """通知配置"""
    enabled: bool = True
    channels: List[NotificationChannel] = [NotificationChannel.INTERNAL]

    # 邮件配置
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    admin_emails: List[str] = []

    # 短信配置（阿里云）
    aliyun_sms_access_key: str = ""
    aliyun_sms_access_secret: str = ""
    aliyun_sms_sign_name: str = ""
    admin_phones: List[str] = []

    # 钉钉配置
    dingtalk_webhook: str = ""
    dingtalk_secret: str = ""

    # 触发条件
    notify_on_error_levels: List[str] = ["error", "critical"]
    rate_limit_seconds: int = 300  # 相同错误 5 分钟内只通知一次


class ErrorNotification:
    """错误通知器"""

    def __init__(self, config: NotificationConfig):
        self.config = config
        self._session = None

    async def send(
        self,
        error_code: str,
        error_details: Dict[str, Any],
        user_id: Optional[int] = None,
        deployment_id: Optional[int] = None,
        notify_admin: bool = True
    ):
        """发送错误通知"""
        if not self.config.enabled:
            return

        if not notify_admin:
            return

        # 检查限流
        if await self._is_rate_limited(error_code):
            logger.info(f"Notification rate limited for {error_code}")
            return

        # 构建通知内容
        from .types import get_error_template
        template = get_error_template(error_code)

        if not template:
            logger.warning(f"No template for error: {error_code}")
            return

        subject = f"[SeraPro 告警] {template.title}"
        message = self._format_message(template, error_details)

        # 发送到各渠道
        tasks = []

        if NotificationChannel.EMAIL in self.config.channels and self.config.admin_emails:
            tasks.append(self._send_email(subject, message))

        if NotificationChannel.SMS in self.config.channels and self.config.admin_phones:
            tasks.append(self._send_sms(template.title))

        if NotificationChannel.DINGTALK in self.config.channels and self.config.dingtalk_webhook:
            tasks.append(self._send_dingtalk(subject, message, error_details))

        if NotificationChannel.INTERNAL in self.config.channels:
            tasks.append(self._create_internal_notification(
                subject, message, user_id, deployment_id, error_code
            ))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Notification task failed: {result}")

    def _format_message(
        self,
        template,
        details: Dict[str, Any]
    ) -> str:
        """格式化消息"""
        message = template.message
        for key, value in details.items():
            message = message.replace(f"{{{key}}}", str(value))

        return f"""【SeraPro 错误告警】

标题：{template.title}
级别：{template.level.value}
分类：{template.category.value}

{message}

【建议操作】
{template.suggested_action}

【时间】
{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

    async def _send_email(self, subject: str, message: str):
        """发送邮件"""
        if not self.config.admin_emails:
            return

        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = self.config.smtp_user
            msg["To"] = ", ".join(self.config.admin_emails)
            msg["Subject"] = subject
            msg.attach(MIMEText(message, "plain", "utf-8"))

            await aiosmtplib.send(
                msg,
                hostname=self.config.smtp_host,
                port=self.config.smtp_port,
                username=self.config.smtp_user,
                password=self.config.smtp_password,
                start_tls=True
            )
            logger.info(f"Email notification sent to {len(self.config.admin_emails)} recipients")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    async def _send_sms(self, message: str):
        """发送短信（阿里云）"""
        if not self.config.admin_phones:
            return

        if not self.config.aliyun_sms_access_key:
            logger.warning("SMS not configured, skipping")
            return

        try:
            # 阿里云短信 API 调用
            # 这里简化实现，实际需要使用阿里云 SDK
            logger.info(f"SMS notification would be sent to {len(self.config.admin_phones)} phones")
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")

    async def _send_dingtalk(self, title: str, message: str, details: Dict):
        """发送钉钉消息"""
        if not self.config.dingtalk_webhook:
            return

        try:
            import aiohttp
            import hmac
            import hashlib
            import base64
            import urllib.parse
            import time

            # 钉钉签名
            timestamp = str(round(time.time() * 1000))
            secret = self.config.dingtalk_secret
            string_to_sign = f'{timestamp}\n{secret}'
            hmac_code = hmac.new(
                secret.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

            url = f'{self.config.dingtalk_webhook}&timestamp={timestamp}&sign={sign}'

            # 钉钉机器人消息格式
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"## {title}\n\n```\n{message}\n```\n\n详情：```{self._truncate(str(details), 500)}```"
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(f"DingTalk notification failed: {resp.status}")
                    else:
                        logger.info("DingTalk notification sent")
        except Exception as e:
            logger.error(f"Failed to send DingTalk notification: {e}")

    async def _create_internal_notification(
        self,
        subject: str,
        message: str,
        user_id: Optional[int],
        deployment_id: Optional[int],
        error_code: str
    ):
        """创建站内通知"""
        try:
            from src.db.database import SessionLocal
            from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey

            # 动态创建或使用现有模型
            class InternalNotificationModel:
                __tablename__ = "internal_notifications"

                id = Column(Integer, primary_key=True)
                title = Column(String(255))
                content = Column(Text)
                error_code = Column(String(50))
                user_id = Column(Integer, ForeignKey("users.id"))
                deployment_id = Column(Integer, ForeignKey("deployments.id"))
                is_read = Column(Boolean, default=False)
                created_at = Column(DateTime, default=datetime.utcnow)

            db = SessionLocal()
            try:
                # 检查表是否存在
                from sqlalchemy import inspect
                inspector = inspect(db.bind)
                if "internal_notifications" not in inspector.get_table_names():
                    logger.warning("internal_notifications table not found, skipping internal notification")
                    return

                notification = InternalNotificationModel(
                    title=subject,
                    content=message,
                    error_code=error_code,
                    user_id=user_id,
                    deployment_id=deployment_id
                )
                db.add(notification)
                db.commit()
                logger.info("Internal notification created")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to create internal notification: {e}")

    def _truncate(self, text: str, max_length: int) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    async def _is_rate_limited(self, error_code: str) -> bool:
        """检查是否限流"""
        try:
            import redis
            from src.config import get_settings

            settings = get_settings()
            r = redis.Redis.from_url(settings.redis_url)

            key = f"notification:rate_limit:{error_code}"
            if r.exists(key):
                return True

            r.setex(key, self.config.rate_limit_seconds, "1")
            return False
        except Exception as e:
            logger.debug(f"Rate limit check failed: {e}")
            return False  # 检查失败时不限制
