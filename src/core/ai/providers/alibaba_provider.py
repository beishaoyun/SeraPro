"""
阿里云 Provider 实现（通义千问）
参考：https://help.aliyun.com/zh/dashscope/
"""

from typing import List, AsyncIterator, Dict

from .base import (
    BaseLLMProvider,
    ProviderConfig,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    ProviderType,
)


class AlibabaProvider(BaseLLMProvider):
    """阿里云通义千问 Provider"""

    @property
    def name(self) -> str:
        return "阿里云"

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """阿里云聊天补全"""
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model or "qwen-max",
            "input": {
                "messages": [m.dict() for m in messages]
            },
            "parameters": {
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
            }
        }

        async with self._session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Alibaba API error: {resp.status} - {error_text}")

            data = await resp.json()

        usage = LLMUsage(
            prompt_tokens=data.get("usage", {}).get("input_tokens", 0),
            completion_tokens=data.get("usage", {}).get("output_tokens", 0),
            total_tokens=data.get("usage", {}).get("total_tokens", 0),
        )
        usage.cost_cny = self._calculate_cost(usage)

        return LLMResponse(
            content=data["output"]["choices"][0]["message"]["content"],
            model=data.get("model", self.config.model),
            usage=usage,
            provider=ProviderType.ALIBABA,
            raw_response=data
        )

    async def stream_chat_completion(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """阿里云流式聊天"""
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model or "qwen-max",
            "input": {
                "messages": [m.dict() for m in messages]
            },
            "parameters": {
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
            },
            "stream": True
        }

        async with self._session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Alibaba API error: {resp.status} - {error_text}")

            # 阿里云 SSE 格式
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        content = chunk["output"]["choices"][0]["message"].get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError):
                        continue

    def get_model_price(self) -> Dict[str, float]:
        """
        阿里云通义千问价格
        参考：https://help.aliyun.com/zh/dashscope/pricing
        """
        prices = {
            "qwen-max": {"input_price_per_1k": 0.04, "output_price_per_1k": 0.12},
            "qwen-plus": {"input_price_per_1k": 0.008, "output_price_per_1k": 0.02},
            "qwen-turbo": {"input_price_per_1k": 0.003, "output_price_per_1k": 0.006},
            "qwen-long": {"input_price_per_1k": 0.0005, "output_price_per_1k": 0.002},
        }
        return prices.get(self.config.model or "qwen-max", prices["qwen-plus"])
