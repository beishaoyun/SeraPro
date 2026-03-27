"""
火山引擎 Provider 实现
参考：https://www.volcengine.com/docs/82379
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


class VolcEngineProvider(BaseLLMProvider):
    """火山引擎 Provider（豆包大模型）"""

    @property
    def name(self) -> str:
        return "火山引擎"

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """火山引擎聊天补全"""
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model or "doubao-pro-32k",  # 豆包大模型
            "messages": [m.dict() for m in messages],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        async with self._session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"VolcEngine API error: {resp.status} - {error_text}")

            data = await resp.json()

        usage = LLMUsage(
            prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
            completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
            total_tokens=data.get("usage", {}).get("total_tokens", 0),
        )
        usage.cost_cny = self._calculate_cost(usage)

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.config.model),
            usage=usage,
            provider=ProviderType.VOLCENGINE,
            raw_response=data
        )

    async def stream_chat_completion(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """火山引擎流式聊天（SSE 格式，类似 OpenAI）"""
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model or "doubao-pro-32k",
            "messages": [m.dict() for m in messages],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }

        async with self._session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"VolcEngine API error: {resp.status} - {error_text}")

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
        火山引擎豆包大模型价格
        参考：https://www.volcengine.com/pricing
        """
        prices = {
            "doubao-pro-32k": {"input_price_per_1k": 0.0008, "output_price_per_1k": 0.002},
            "doubao-lite-32k": {"input_price_per_1k": 0.0003, "output_price_per_1k": 0.0006},
            "doubao-pro-4k": {"input_price_per_1k": 0.00008, "output_price_per_1k": 0.0002},
        }
        model_key = self.config.model or "doubao-pro-32k"
        return prices.get(model_key, prices["doubao-lite-32k"])
