"""
OpenAI Provider 实现
"""

from typing import List, Dict, Any, AsyncIterator
import aiohttp
import json

from .base import (
    BaseLLMProvider,
    ProviderConfig,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    ProviderType,
)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider"""

    @property
    def name(self) -> str:
        return "OpenAI"

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """OpenAI 聊天补全"""
        url = (self.config.base_url or "https://api.openai.com/v1") + "/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model,
            "messages": [m.dict() for m in messages],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        async with self._session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"OpenAI API error: {resp.status} - {error_text}")

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
            provider=ProviderType.OPENAI,
            raw_response=data
        )

    async def stream_chat_completion(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """OpenAI 流式聊天"""
        url = (self.config.base_url or "https://api.openai.com/v1") + "/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model,
            "messages": [m.dict() for m in messages],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }

        async with self._session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"OpenAI API error: {resp.status} - {error_text}")

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
        """OpenAI 价格 (美元转人民币，按 7.2)"""
        # https://openai.com/api/pricing/
        prices = {
            "gpt-4": {"input_price_per_1k": 0.03 * 7.2, "output_price_per_1k": 0.06 * 7.2},
            "gpt-4-turbo": {"input_price_per_1k": 0.01 * 7.2, "output_price_per_1k": 0.03 * 7.2},
            "gpt-3.5-turbo": {"input_price_per_1k": 0.0005 * 7.2, "output_price_per_1k": 0.0015 * 7.2},
        }
        return prices.get(self.config.model, prices["gpt-3.5-turbo"])
