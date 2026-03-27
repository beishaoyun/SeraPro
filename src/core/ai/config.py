"""
多 AI Provider 配置
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, Optional, List
from .providers.base import ProviderType


class AIProviderSettings(BaseSettings):
    """多 AI Provider 设置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_"
    )

    # ========== OpenAI ==========
    openai_api_key: str = ""
    openai_enabled: bool = True
    openai_base_url: Optional[str] = None  # 可配置代理
    openai_model: str = "gpt-3.5-turbo"

    # ========== 火山引擎 ==========
    volcengine_api_key: str = ""
    volcengine_enabled: bool = True
    volcengine_model: str = "doubao-pro-32k"

    # ========== 阿里云 ==========
    alibaba_api_key: str = ""
    alibaba_enabled: bool = True
    alibaba_model: str = "qwen-plus"

    # ========== DeepSeek ==========
    deepseek_api_key: str = ""
    deepseek_enabled: bool = True
    deepseek_model: str = "deepseek-chat"

    # ========== 默认 Provider 和模型 ==========
    default_provider: ProviderType = ProviderType.VOLCENGINE  # 默认火山引擎

    # ========== 路由策略 ==========
    routing_strategy: str = "weighted_random"  # weighted_random, cheapest, first_available

    # ========== 成本优化 ==========
    cost_optimization_enabled: bool = False  # 自动选择最便宜的可用 Provider

    def get_enabled_providers(self) -> List[ProviderType]:
        """获取启用的 Provider 列表"""
        enabled = []
        if self.openai_enabled and self.openai_api_key:
            enabled.append(ProviderType.OPENAI)
        if self.volcengine_enabled and self.volcengine_api_key:
            enabled.append(ProviderType.VOLCENGINE)
        if self.alibaba_enabled and self.alibaba_api_key:
            enabled.append(ProviderType.ALIBABA)
        if self.deepseek_enabled and self.deepseek_api_key:
            enabled.append(ProviderType.DEEPSEEK)
        return enabled or [ProviderType.VOLCENGINE]  # 至少返回一个

    def create_router_config(self):
        """创建路由器配置"""
        from .providers import ProviderConfig, create_provider

        provider_configs = []

        if self.openai_enabled and self.openai_api_key:
            provider_configs.append((
                ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key=self.openai_api_key,
                    base_url=self.openai_base_url,
                    model=self.openai_model,
                ),
                type(create_provider(ProviderConfig(
                    provider_type=ProviderType.OPENAI,
                    api_key=self.openai_api_key,
                    model=self.openai_model
                )))
            ))

        if self.volcengine_enabled and self.volcengine_api_key:
            from .providers import VolcEngineProvider
            provider_configs.append((
                ProviderConfig(
                    provider_type=ProviderType.VOLCENGINE,
                    api_key=self.volcengine_api_key,
                    model=self.volcengine_model,
                ),
                VolcEngineProvider
            ))

        if self.alibaba_enabled and self.alibaba_api_key:
            from .providers import AlibabaProvider
            provider_configs.append((
                ProviderConfig(
                    provider_type=ProviderType.ALIBABA,
                    api_key=self.alibaba_api_key,
                    model=self.alibaba_model,
                ),
                AlibabaProvider
            ))

        if self.deepseek_enabled and self.deepseek_api_key:
            from .providers import DeepSeekProvider
            provider_configs.append((
                ProviderConfig(
                    provider_type=ProviderType.DEEPSEEK,
                    api_key=self.deepseek_api_key,
                    model=self.deepseek_model,
                ),
                DeepSeekProvider
            ))

        return provider_configs


# 单例实例
_settings: Optional[AIProviderSettings] = None


def get_settings() -> AIProviderSettings:
    """获取设置单例"""
    global _settings
    if _settings is None:
        _settings = AIProviderSettings()
    return _settings
