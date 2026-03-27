"""
AI Provider 路由器 - 负载均衡和故障转移
"""

from typing import List, Dict, Optional, Tuple
from .base import BaseLLMProvider, ProviderConfig, LLMMessage, LLMResponse, ProviderType
from .factory import create_provider
import logging
import random

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Provider 路由器"""

    def __init__(self, providers: List[Tuple[ProviderConfig, type]]):
        """
        初始化路由器

        Args:
            providers: [(ProviderConfig, ProviderClass), ...]
        """
        self.providers: List[BaseLLMProvider] = []
        self.provider_weights: List[float] = []
        self._init_providers(providers)

    def _init_providers(self, provider_configs: List[Tuple[ProviderConfig, type]]):
        """初始化所有 Provider"""
        for config, provider_class in provider_configs:
            try:
                provider = provider_class(config)
                self.providers.append(provider)
                # 默认权重相同
                self.provider_weights.append(1.0)
                logger.info(f"Initialized provider: {provider.name}")
            except Exception as e:
                logger.warning(f"Failed to initialize provider {config.provider_type}: {e}")

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        strategy: str = "weighted_random",
        **kwargs
    ) -> LLMResponse:
        """
        路由聊天请求

        Args:
            messages: 消息列表
            strategy: 路由策略
                - weighted_random: 按权重随机选择
                - cheapest: 选择最便宜的
                - first_available: 选择第一个可用的
            **kwargs: 额外参数

        Returns:
            LLMResponse: 响应
        """
        if not self.providers:
            raise Exception("No providers available")

        # 选择 Provider
        if strategy == "cheapest":
            provider = min(
                self.providers,
                key=lambda p: p.get_model_price()["input_price_per_1k"]
            )
        elif strategy == "first_available":
            provider = self.providers[0]
        else:  # weighted_random
            provider = random.choices(
                self.providers,
                weights=self.provider_weights
            )[0]

        # 尝试调用，失败则故障转移
        last_error = None
        for i, p in enumerate(self.providers):
            try:
                return await p.chat_completion(messages, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {p.name} failed: {e}")
                if i < len(self.providers) - 1:
                    logger.info("Failing over to next provider...")
                    continue

        raise Exception(f"All providers failed. Last error: {last_error}")

    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        results = {}
        for provider in self.providers:
            try:
                # 简单健康检查：调用一个空消息
                await provider.chat_completion([LLMMessage(role="user", content="ping")])
                results[provider.name] = True
            except Exception as e:
                logger.warning(f"Health check failed for {provider.name}: {e}")
                results[provider.name] = False
        return results

    def get_provider_by_type(self, provider_type: ProviderType) -> Optional[BaseLLMProvider]:
        """根据类型获取 Provider"""
        for provider in self.providers:
            if provider.config.provider_type == provider_type:
                return provider
        return None

    def get_available_providers(self) -> List[str]:
        """获取可用的 Provider 名称列表"""
        return [p.name for p in self.providers]
