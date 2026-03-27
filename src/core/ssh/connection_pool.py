"""
SSH 连接池模块

设计要点:
- 连接复用，避免频繁创建/销毁
- 空闲连接自动清理
- 并发连接数限制
- 健康检查
"""

import asyncio
import time
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
import logging

from src.core.ssh.client import SSHClient, SSHCredentials

logger = logging.getLogger(__name__)


@dataclass
class PooledConnection:
    """池化连接"""
    client: SSHClient
    credentials: SSHCredentials
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0
    is_in_use: bool = False


class SSHConnectionPool:
    """
    SSH 连接池

    特性:
    - 按服务器 ID 复用连接
    - 最大连接数限制
    - 空闲超时自动关闭
    - 健康检查
    """

    def __init__(
        self,
        max_connections: int = 20,
        idle_timeout: int = 600,  # 10 分钟
        max_uses: int = 100,  # 最大使用次数后重建连接
    ):
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self.max_uses = max_uses

        # 连接池存储
        self._pool: Dict[str, PooledConnection] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

        # 启动空闲清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = True

    async def start(self):
        """启动连接池"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"SSH 连接池已启动 (max={self.max_connections})")

    async def stop(self):
        """停止连接池"""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # 关闭所有连接
        for server_id, pooled in list(self._pool.items()):
            await pooled.client.disconnect()
            logger.info(f"SSH 连接池已关闭：{server_id}")

        self._pool.clear()
        self._locks.clear()

    async def acquire(self, server_id: str, credentials: SSHCredentials) -> SSHClient:
        """
        获取连接

        Args:
            server_id: 服务器唯一标识
            credentials: SSH 凭证

        Returns:
            SSH 客户端
        """
        lock = self._get_lock(server_id)

        async with lock:
            # 检查池中是否有可用连接
            if server_id in self._pool:
                pooled = self._pool[server_id]

                if not pooled.is_in_use:
                    # 检查是否需要重建连接
                    if self._is_connection_stale(pooled):
                        logger.info(f"连接已过期，重建：{server_id}")
                        await pooled.client.disconnect()
                        pooled.client = SSHClient()
                        await pooled.client.connect(credentials)
                        pooled.created_at = time.time()
                        pooled.use_count = 0
                    else:
                        # 健康检查
                        is_healthy = await self._health_check(pooled.client)
                        if not is_healthy:
                            logger.warning(f"连接不健康，重建：{server_id}")
                            pooled.client = SSHClient()
                            await pooled.client.connect(credentials)
                            pooled.created_at = time.time()
                            pooled.use_count = 0

                    # 标记为使用中
                    pooled.is_in_use = True
                    pooled.last_used_at = time.time()
                    pooled.use_count += 1

                    logger.debug(f"复用连接：{server_id} (use_count={pooled.use_count})")
                    return pooled.client

            # 创建新连接
            logger.info(f"创建新连接：{server_id}")
            client = SSHClient()
            connected = await client.connect(credentials)

            if not connected:
                raise ConnectionError(f"无法连接到 SSH 服务器：{credentials.host}:{credentials.port}")

            # 如果池已满，关闭最旧的连接
            if len(self._pool) >= self.max_connections:
                await self._evict_oldest()

            # 添加到池中 (use_count 初始为 1 表示已使用一次)
            self._pool[server_id] = PooledConnection(
                client=client,
                credentials=credentials,
                is_in_use=True,
                use_count=1
            )

            return client

    def release(self, server_id: str):
        """
        释放连接

        Args:
            server_id: 服务器 ID
        """
        if server_id not in self._pool:
            return

        pooled = self._pool[server_id]
        pooled.is_in_use = False
        pooled.last_used_at = time.time()

        logger.debug(f"释放连接：{server_id}")

    def _get_lock(self, server_id: str) -> asyncio.Lock:
        """获取服务器锁"""
        if server_id not in self._locks:
            self._locks[server_id] = asyncio.Lock()
        return self._locks[server_id]

    def _is_connection_stale(self, pooled: PooledConnection) -> bool:
        """检查连接是否过期"""
        age = time.time() - pooled.created_at
        idle_time = time.time() - pooled.last_used_at

        # 超过最大使用次数
        if pooled.use_count >= self.max_uses:
            return True

        # 空闲超时
        if idle_time > self.idle_timeout:
            return True

        # 连接存活超过 24 小时
        if age > 86400:
            return True

        return False

    async def _health_check(self, client: SSHClient) -> bool:
        """健康检查"""
        if not client.connected:
            return False

        try:
            # 执行简单命令检查连接
            result = await client.execute("echo health_check", timeout=5)
            return result["exit_code"] == 0
        except Exception:
            return False

    async def _evict_oldest(self):
        """移除最久未使用的连接"""
        oldest_id = None
        oldest_time = float('inf')

        for server_id, pooled in self._pool.items():
            if not pooled.is_in_use and pooled.last_used_at < oldest_time:
                oldest_id = server_id
                oldest_time = pooled.last_used_at

        if oldest_id:
            await self._pool[oldest_id].client.disconnect()
            del self._pool[oldest_id]
            logger.info(f"移除最旧连接：{oldest_id}")

    async def _cleanup_loop(self):
        """空闲连接清理循环"""
        while self._running:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._cleanup_idle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务出错：{e}")

    async def _cleanup_idle(self):
        """清理空闲超时连接"""
        to_remove = []

        for server_id, pooled in self._pool.items():
            if not pooled.is_in_use:
                idle_time = time.time() - pooled.last_used_at
                if idle_time > self.idle_timeout:
                    to_remove.append(server_id)

        for server_id in to_remove:
            await self._pool[server_id].client.disconnect()
            del self._pool[server_id]
            logger.info(f"清理空闲连接：{server_id}")

    def get_stats(self) -> Dict:
        """获取连接池统计"""
        now = time.time()
        return {
            "total_connections": len(self._pool),
            "in_use": sum(1 for p in self._pool.values() if p.is_in_use),
            "idle": sum(1 for p in self._pool.values() if not p.is_in_use),
            "avg_age_seconds": (
                sum(now - p.created_at for p in self._pool.values()) / len(self._pool)
                if self._pool else 0
            ),
            "total_use_count": sum(p.use_count for p in self._pool.values())
        }


# 全局连接池实例
_pool: Optional[SSHConnectionPool] = None


def get_connection_pool() -> SSHConnectionPool:
    """获取全局连接池实例"""
    global _pool
    if _pool is None:
        _pool = SSHConnectionPool()
    return _pool


async def init_connection_pool(**kwargs):
    """初始化连接池"""
    global _pool
    _pool = SSHConnectionPool(**kwargs)
    await _pool.start()
    logger.info("全局 SSH 连接池已初始化")


async def close_connection_pool():
    """关闭全局连接池"""
    global _pool
    if _pool:
        await _pool.stop()
        _pool = None
