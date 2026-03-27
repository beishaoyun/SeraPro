"""
AI Provider 工厂 - 根据配置创建 Provider 实例
"""

from typing import Type, Dict
from .base import BaseLLMProvider, ProviderConfig, ProviderType
from .openai_provider import OpenAIProvider
from .volcengine_provider import VolcEngineProvider
from .alibaba_provider import AlibabaProvider
from .deepseek_provider import DeepSeekProvider


# Provider 类型映射
PROVIDER_REGISTRY: Dict[ProviderType, Type[BaseLLMProvider]] = {
    ProviderType.OPENAI: OpenAIProvider,
    ProviderType.VOLCENGINE: VolcEngineProvider,
    ProviderType.ALIBABA: AlibabaProvider,
    ProviderType.DEEPSEEK: DeepSeekProvider,
}


def create_provider(config: ProviderConfig) -> BaseLLMProvider:
    """
    根据配置创建 Provider 实例

    Args:
        config: Provider 配置

    Returns:
        Provider 实例
    """
    provider_class = PROVIDER_REGISTRY.get(config.provider_type)
    if not provider_class:
        raise ValueError(f"Unknown provider type: {config.provider_type}")

    return provider_class(config)


def get_available_providers() -> list[ProviderType]:
    """获取所有可用的 Provider 类型"""
    return list(PROVIDER_REGISTRY.keys())
