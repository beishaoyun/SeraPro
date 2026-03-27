"""
DeepSeek Provider 实现
参考：https://platform.deepseek.com/api-docs/
"""

from typing import List, AsyncIterator, Dict
import json

from .base import (
    BaseLLMProvider,
    ProviderConfig,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    ProviderType,
)


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek Provider"""

    @property
    def name(self) -> str:
        return "DeepSeek"

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """DeepSeek 聊天补全"""
        url = "https://api.deepseek.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model or "deepseek-chat",
            "messages": [m.dict() for m in messages],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        async with self._session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"DeepSeek API error: {resp.status} - {error_text}")

            data = await resp.json()

        usage = LLMUsage(
            prompt_tokens=data["usage"]["prompt_tokens"],
            completion_tokens=data["usage"]["completion_tokens"],
            total_tokens=data["usage"]["total_tokens"],
        )
        usage.cost_cny = self._calculate_cost(usage)

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data["model"],
            usage=usage,
            provider=ProviderType.DEEPSEEK,
            raw_response=data
        )

    async def stream_chat_completion(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """DeepSeek 流式聊天"""
        url = "https://api.deepseek.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model or "deepseek-chat",
            "messages": [m.dict() for m in messages],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }

        async with self._session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"DeepSeek API error: {resp.status} - {error_text}")

            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    def get_model_price(self) -> Dict[str, float]:
        """
        DeepSeek 价格
        参考：https://platform.deepseek.com/pricing
        价格非常便宜
        """
        return {
            "input_price_per_1k": 0.001,  # 1 元/百万 tokens
            "output_price_per_1k": 0.002,  # 2 元/百万 tokens
        }
