"""
AI Provider 抽象基类 - 统一多平台 API 接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from pydantic import BaseModel, Field
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """支持的 AI 平台"""
    OPENAI = "openai"
    VOLCENGINE = "volcengine"      # 火山引擎
    ALIBABA = "alibaba"            # 阿里云
    DEEPSEEK = "deepseek"
    MOONSHOT = "moonshot"          # 月之暗面


class LLMMessage(BaseModel):
    """统一消息格式"""
    role: str = Field(..., description="角色：system/user/assistant")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(None, description="可选的名称")


class LLMUsage(BaseModel):
    """Token 使用统计"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_cny: Optional[float] = None  # 估算成本 (人民币)


class LLMResponse(BaseModel):
    """统一响应格式"""
    content: str
    model: str
    usage: LLMUsage
    provider: ProviderType
    raw_response: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProviderConfig(BaseModel):
    """Provider 配置"""
    provider_type: ProviderType
    api_key: str
    base_url: Optional[str] = None
    model: str
    max_tokens: int = 2000
    temperature: float = 0.3
    timeout_seconds: int = 60
    retry_count: int = 3


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类"""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._session = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称"""
        pass

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """
        聊天补全接口

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            LLMResponse: 响应
        """
        pass

    @abstractmethod
    async def stream_chat_completion(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式聊天补全

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Yields:
            逐块返回内容
        """
        pass

    @abstractmethod
    def get_model_price(self) -> Dict[str, float]:
        """
        获取模型价格

        Returns:
            {"input_price_per_1k": float, "output_price_per_1k": float}
        """
        pass

    async def __aenter__(self):
        self._session = await self._create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def _create_session(self):
        """创建 HTTP Session"""
        import aiohttp
        return aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        )

    def _calculate_cost(self, usage: LLMUsage) -> float:
        """计算成本"""
        pricing = self.get_model_price()
        input_cost = (usage.prompt_tokens / 1000) * pricing["input_price_per_1k"]
        output_cost = (usage.completion_tokens / 1000) * pricing["output_price_per_1k"]
        return round(input_cost + output_cost, 4)
