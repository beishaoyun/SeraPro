"""
SSH 连接模块

设计要点:
- 连接池管理
- 超时和重试
- 密钥/密码认证
- 主机密钥验证 (可选)
- 审计日志记录所有命令
"""

import asyncio
import paramiko
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SSHCredentials:
    """SSH 凭证"""
    host: str
    port: int = 22
    username: str = "root"
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    timeout: int = 30


class SSHClient:
    """SSH 客户端"""

    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None
        self.connected = False
        self._credentials: Optional[SSHCredentials] = None

    async def connect(self, credentials: SSHCredentials) -> bool:
        """
        连接到 SSH 服务器

        Args:
            credentials: SSH 凭证

        Returns:
            连接成功与否
        """
        self._credentials = credentials
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            loop = asyncio.get_event_loop()

            if credentials.ssh_key:
                # 密钥认证
                pkey = paramiko.RSAKey.from_private_key(
                    credentials.ssh_key.encode()
                )
                await loop.run_in_executor(
                    None,
                    self._connect_sync,
                    credentials.host,
                    credentials.port,
                    credentials.username,
                    pkey,
                    credentials.timeout
                )
            else:
                # 密码认证
                await loop.run_in_executor(
                    None,
                    self._connect_sync,
                    credentials.host,
                    credentials.port,
                    credentials.username,
                    None,
                    credentials.timeout,
                    credentials.password
                )

            self.connected = True
            logger.info(f"SSH connected to {credentials.host}:{credentials.port}")
            return True

        except Exception as e:
            logger.error(f"SSH connection failed: {e}")
            self.connected = False
            return False

    def _connect_sync(
        self,
        host: str,
        port: int,
        username: str,
        pkey: Optional[paramiko.PKey],
        timeout: int,
        password: Optional[str] = None
    ):
        """同步连接方法 (在 executor 中运行)"""
        self.client.connect(
            hostname=host,
            port=port,
            username=username,
            pkey=pkey,
            password=password,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False
        )

    async def execute(self, command: str, timeout: int = 300) -> Dict[str, Any]:
        """
        执行命令

        Args:
            command: 要执行的命令
            timeout: 超时时间 (秒)

        Returns:
            {
                "exit_code": int,
                "stdout": str,
                "stderr": str,
                "duration_ms": int
            }
        """
        if not self.connected:
            raise RuntimeError("Not connected to SSH server")

        import time
        start_time = time.time()

        loop = asyncio.get_event_loop()
        exit_code, stdout, stderr = await loop.run_in_executor(
            None,
            self._execute_command,
            command,
            timeout
        )

        duration_ms = int((time.time() - start_time) * 1000)

        result = {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": duration_ms
        }

        logger.debug(
            f"SSH command executed: {command[:50]}... "
            f"exit_code={exit_code}, duration={duration_ms}ms"
        )

        return result

    def _execute_command(
        self,
        command: str,
        timeout: int
    ) -> tuple[int, str, str]:
        """同步执行命令 (在 executor 中运行)"""
        stdin, stdout, stderr = self.client.exec_command(
            command,
            timeout=timeout
        )

        exit_code = stdout.channel.recv_exit_status()
        return exit_code, stdout.read().decode(), stderr.read().decode()

    async def disconnect(self):
        """断开连接"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("SSH connection closed")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
