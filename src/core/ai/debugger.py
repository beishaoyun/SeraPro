"""
AI 排错模块 - 智能错误分析和修复建议

功能:
- 分析部署错误日志
- 从知识库检索相似案例
- 生成修复建议
- 支持对话式排错
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from src.core.ai.providers import (
    LLMMessage,
    ProviderRouter,
    ProviderConfig,
    ProviderType,
)

logger = logging.getLogger(__name__)


class DebugResult(BaseModel):
    """排错结果"""
    analysis: str = Field(..., description="错误分析")
    solution: str = Field(..., description="解决方案")
    commands: List[str] = Field(default_factory=list, description="修复命令列表")
    confidence: float = Field(..., description="置信度 (0-1)")
    knowledge_references: List[Dict] = Field(default_factory=list, description="知识库参考")


class AIDebugger:
    """AI 排错器"""

    def __init__(self, provider_router: ProviderRouter):
        self.provider_router = provider_router
        self.conversation_history: Dict[int, List[LLMMessage]] = {}  # deployment_id -> messages

    async def analyze(
        self,
        failed_step: Any,
        previous_steps: List[Any],
        os_type: str = "ubuntu",
        os_version: str = "22.04",
        service_type: str = "web"
    ) -> DebugResult:
        """
        分析错误并生成修复建议

        Args:
            failed_step: 失败的步骤
            previous_steps: 之前的步骤列表
            os_type: 操作系统类型
            os_version: 操作系统版本
            service_type: 服务类型

        Returns:
            DebugResult: 排错结果
        """
        # 构建错误上下文
        error_context = self._build_error_context(
            failed_step, previous_steps, os_type, os_version, service_type
        )

        # 构建 Prompt
        messages = [
            LLMMessage(
                role="system",
                content=self._get_system_prompt()
            ),
            LLMMessage(
                role="user",
                content=error_context
            )
        ]

        # 调用 LLM
        try:
            response = await self.provider_router.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )

            # 解析响应
            result = self._parse_llm_response(response.content)
            logger.info(f"AI Debug analysis completed: confidence={result.confidence}")
            return result

        except Exception as e:
            logger.error(f"AI Debug analysis failed: {e}")
            return DebugResult(
                analysis=f"AI 分析失败：{str(e)}",
                solution="请手动检查错误日志并尝试解决问题。",
                commands=[],
                confidence=0.0
            )

    def _build_error_context(
        self,
        failed_step: Any,
        previous_steps: List[Any],
        os_type: str,
        os_version: str,
        service_type: str
    ) -> str:
        """构建错误上下文"""
        context = f"""
【部署环境】
- 操作系统：{os_type} {os_version}
- 服务类型：{service_type}

【已执行的步骤】
"""
        for step in previous_steps:
            status = "✓" if step.status == "success" else "✗"
            context += f"{status} 步骤 {step.number}: {step.description}\n"
            if step.command:
                context += f"  命令：{step.command}\n"
            if step.output:
                context += f"  输出：{step.output[:200]}...\n"

        context += f"""
【失败的步骤】
步骤 {failed_step.number}: {failed_step.description}
命令：{failed_step.command or 'N/A'}
错误信息：{failed_step.error_message or 'Unknown error'}

请分析错误原因并提供修复方案。
"""
        return context

    def _get_system_prompt(self) -> str:
        """获取系统 Prompt"""
        return """
你是一个专业的 DevOps 工程师，专门帮助解决服务器部署问题。

你的任务：
1. 分析部署错误日志，找出根本原因
2. 提供详细的解决方案
3. 给出具体可执行的修复命令
4. 评估解决方案的置信度

请按照以下 JSON 格式输出：
{
    "analysis": "错误原因分析",
    "solution": "解决方案描述",
    "commands": ["修复命令 1", "修复命令 2"],
    "confidence": 0.85,
    "knowledge_references": []
}

注意：
- 命令要具体可执行
- 考虑用户的操作系统版本
- 如果不确定，给出多个可能的解决方案
- 置信度范围 0-1，1 表示非常确定
"""

    def _parse_llm_response(self, content: str) -> DebugResult:
        """解析 LLM 响应"""
        import json
        import re

        # 尝试提取 JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return DebugResult(
                    analysis=data.get("analysis", content),
                    solution=data.get("solution", ""),
                    commands=data.get("commands", []),
                    confidence=float(data.get("confidence", 0.5)),
                    knowledge_references=data.get("knowledge_references", [])
                )
            except json.JSONDecodeError:
                pass

        # 解析失败，返回原始内容
        return DebugResult(
            analysis=content,
            solution="请查看 AI 分析结果。",
            commands=[],
            confidence=0.5
        )

    async def chat(
        self,
        deployment_id: int,
        user_message: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        对话式排错

        Args:
            deployment_id: 部署 ID
            user_message: 用户消息
            context: 额外上下文

        Returns:
            AI 回复
        """
        # 获取或创建对话历史
        if deployment_id not in self.conversation_history:
            self.conversation_history[deployment_id] = [
                LLMMessage(
                    role="system",
                    content="""你是一个专业的 DevOps 助手，通过对话帮助用户解决部署问题。
请用简洁清晰的中文回答，必要时提供具体的命令。"""
                )
            ]

        # 添加用户消息
        messages = self.conversation_history[deployment_id]
        messages.append(LLMMessage(role="user", content=user_message))

        # 调用 LLM
        response = await self.provider_router.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        # 保存 AI 回复到历史
        messages.append(LLMMessage(role="assistant", content=response.content))

        # 限制历史记录长度
        if len(messages) > 20:  # 保留最近 10 轮对话
            self.conversation_history[deployment_id] = [messages[0]] + messages[-10:]

        return response.content

    def clear_conversation(self, deployment_id: int):
        """清除对话历史"""
        if deployment_id in self.conversation_history:
            del self.conversation_history[deployment_id]
