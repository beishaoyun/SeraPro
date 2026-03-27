"""
缓存策略模块

设计要点:
- Redis 作为缓存后端
- 缓存装饰器简化使用
- 自动过期
- 缓存穿透/击穿/雪崩防护
"""

import asyncio
import hashlib
import json
import time
from functools import wraps
from typing import Any, Optional, Callable, Union
from dataclasses import dataclass
import logging

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_at: float
    ttl: int
    hit_count: int = 0


class CacheManager:
    """
    缓存管理器

    特性:
    - Redis 缓存后端
    - 内存缓存作为 L1 缓存
    - 缓存穿透防护 (空值缓存)
    - 缓存击穿防护 (互斥锁)
    - 缓存雪崩防护 (随机 TTL)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/1",
        default_ttl: int = 300,
        max_memory_items: int = 1000,
        use_memory_cache: bool = True
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.max_memory_items = max_memory_items
        self.use_memory_cache = use_memory_cache

        self._redis: Optional[redis.Redis] = None
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

        # 统计
        self._hits = 0
        self._misses = 0

    async def connect(self):
        """连接到 Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis 客户端未安装，缓存功能不可用")
            return False

        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis.ping()
            logger.info("已连接到 Redis 缓存")
            return True
        except Exception as e:
            logger.warning(f"Redis 连接失败，使用内存缓存：{e}")
            return True  # 降级使用内存缓存

    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps(
            {"args": args, "kwargs": kwargs},
        sort_keys=True,
            default=str
        )
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    def _get_lock(self, key: str) -> asyncio.Lock:
        """获取键的锁"""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        # 尝试 L1 内存缓存
        if self.use_memory_cache and key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() - entry.created_at < entry.ttl:
                entry.hit_count += 1
                self._hits += 1
                logger.debug(f"L1 缓存命中：{key}")
                return entry.value
            else:
                del self._memory_cache[key]

        # 尝试 Redis
        if not self._redis:
            self._misses += 1
            return None

        try:
            data = await self._redis.get(key)
            if data:
                value = json.loads(data)
                self._hits += 1

                # 更新 L1 缓存
                if self.use_memory_cache:
                    self._maybe_add_to_memory(key, value)

                logger.debug(f"Redis 缓存命中：{key}")
                return value
        except Exception as e:
            logger.error(f"Redis 获取失败：{e}")

        self._misses += 1
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        add_jitter: bool = True
    ):
        """设置缓存"""
        actual_ttl = ttl or self.default_ttl

        # 添加随机抖动防止雪崩
        if add_jitter:
            jitter = int(actual_ttl * 0.1)  # ±10%
            actual_ttl += asyncio.get_event_loop().time() % (jitter * 2) - jitter
            actual_ttl = max(1, int(actual_ttl))

        # 设置 L1 缓存
        if self.use_memory_cache:
            self._maybe_add_to_memory(key, value, actual_ttl)

        # 设置 Redis
        if self._redis:
            try:
                await self._redis.setex(
                    key,
                    actual_ttl,
                    json.dumps(value, default=str)
                )
            except Exception as e:
                logger.error(f"Redis 设置失败：{e}")

    def _maybe_add_to_memory(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """添加 item 到内存缓存 (带 LRU 淘汰)"""
        if len(self._memory_cache) >= self.max_memory_items:
            # LRU 淘汰
            oldest_key = min(
                self._memory_cache.keys(),
                key=lambda k: self._memory_cache[k].last_accessed
            )
            del self._memory_cache[oldest_key]

        self._memory_cache[key] = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl=ttl or self.default_ttl
        )

    async def delete(self, key: str):
        """删除缓存"""
        if key in self._memory_cache:
            del self._memory_cache[key]

        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception as e:
                logger.error(f"Redis 删除失败：{e}")

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if key in self._memory_cache:
            return True

        if self._redis:
            try:
                return await self._redis.exists(key)
            except Exception:
                pass

        return False

    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取或设置缓存 (带互斥锁防止击穿)

        Args:
            key: 缓存键
            factory: 缓存未命中时的工厂函数 (async)
            ttl: 过期时间

        Returns:
            缓存值
        """
        # 尝试获取
        cached = await self.get(key)
        if cached is not None:
            return cached

        # 获取互斥锁
        lock = self._get_lock(key)

        async with lock:
            # 双重检查
            cached = await self.get(key)
            if cached is not None:
                return cached

            # 执行工厂函数
            logger.debug(f"缓存未命中，执行工厂：{key}")
            value = await factory()

            # 即使为空也缓存 (防止穿透)
            await self.set(key, value, ttl)

            return value

    def cached(
        self,
        key_prefix: str,
        ttl: Optional[int] = None,
        condition: Optional[Callable[[Any], bool]] = None
    ):
        """
        缓存装饰器

        Args:
            key_prefix: 键前缀
            ttl: 过期时间
            condition: 可选，决定是否缓存结果的函数

        Example:
            @cache.cached("user:profile", ttl=600)
            async def get_user_profile(user_id: int):
                ...
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                key = self._make_key(key_prefix, *args, **kwargs)

                # 尝试获取缓存
                cached = await self.get(key)
                if cached is not None:
                    return cached

                # 执行函数
                result = await func(*args, **kwargs)

                # 检查条件
                if condition is None or condition(result):
                    await self.set(key, result, ttl)

                return result
            return wrapper
        return decorator

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "memory_cache_size": len(self._memory_cache),
            "redis_connected": self._redis is not None
        }


# 全局缓存实例
_cache: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """获取全局缓存实例"""
    global _cache
    if _cache is None:
        _cache = CacheManager()
    return _cache


async def init_cache(redis_url: str = "redis://localhost:6379/1", **kwargs):
    """初始化全局缓存"""
    global _cache
    _cache = CacheManager(redis_url=redis_url, **kwargs)
    await _cache.connect()


async def close_cache():
    """关闭全局缓存"""
    global _cache
    if _cache:
        await _cache.close()
        _cache = None


# =========== 特定场景的缓存函数 ===========

async def cache_knowledge_search(
    query: str,
    os_filter: Optional[str] = None,
    service_type: Optional[str] = None
) -> Optional[str]:
    """缓存知识库搜索结果"""
    cache = get_cache()
    key = cache._make_key(
        "knowledge:search",
        query=query,
        os_filter=os_filter,
        service_type=service_type
    )
    return key


async def cache_server_credentials(server_id: int) -> str:
    """缓存服务器凭证"""
    cache = get_cache()
    key = cache._make_key("server:credentials", server_id=server_id)
    return key


async def cache_deployment_logs(deployment_id: int) -> str:
    """缓存部署日志"""
    cache = get_cache()
    key = cache._make_key("deployment:logs", deployment_id=deployment_id)
    return key
