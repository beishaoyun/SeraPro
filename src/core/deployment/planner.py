"""
部署计划生成模块

功能:
- 解析 GitHub README 文件
- 使用 LLM 识别部署步骤
- 生成结构化的部署计划
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import re

from src.core.ai.providers.router import ProviderRouter
from src.core.ai.providers.base import LLMMessage
from src.core.deployment.executor import DeployPlan, DeployStep

logger = logging.getLogger(__name__)


@dataclass
class ParsedTutorial:
    """解析后的教程"""
    title: str
    description: str
    steps: List[Dict[str, Any]]
    service_type: str
    os_requirements: Dict[str, str]


class DeployPlanner:
    """部署计划生成器"""

    def __init__(self, provider_router: ProviderRouter):
        self.provider_router = provider_router

    async def generate_plan(
        self,
        github_url: str,
        readme_content: str,
        os_type: str = "ubuntu",
        os_version: str = "22.04"
    ) -> DeployPlan:
        """
        根据 README 内容生成部署计划

        Args:
            github_url: GitHub 项目地址
            readme_content: README 文件内容
            os_type: 操作系统类型
            os_version: 操作系统版本

        Returns:
            DeployPlan: 部署计划
        """
        # 使用 LLM 解析 README，提取部署步骤
        steps = await self._parse_readme_with_llm(
            readme_content, os_type, os_version
        )

        # 识别服务类型
        service_type = self._identify_service_type(readme_content)

        logger.info(
            f"Generated deployment plan: {len(steps)} steps, "
            f"service_type={service_type}"
        )

        return DeployPlan(
            github_url=github_url,
            service_type=service_type,
            steps=steps
        )

    async def _parse_readme_with_llm(
        self,
        readme_content: str,
        os_type: str,
        os_version: str
    ) -> List[DeployStep]:
        """使用 LLM 解析 README，提取部署步骤"""

        system_prompt = """
你是一个专业的 DevOps 工程师，专门分析 GitHub 项目的 README 文件，提取部署步骤。

你的任务:
1. 分析 README 内容，识别安装和部署相关的步骤
2. 提取每个步骤的描述和对应的 shell 命令
3. 按照正确的执行顺序排列步骤
4. 考虑目标操作系统 (Ubuntu/CentOS/Debian) 调整命令

输出格式 (JSON):
{
    "steps": [
        {
            "description": "步骤描述",
            "command": "shell 命令 (如果没有命令则为 null)"
        }
    ]
}

注意:
- 只提取与部署相关的步骤
- 命令要完整可执行
- 根据操作系统调整包管理命令 (apt/yum/dnf)
- 跳过与部署无关的内容 (如功能介绍、API 文档等)
"""

        user_prompt = f"""
请分析以下 README 内容，提取部署步骤。

目标操作系统：{os_type} {os_version}

README 内容:
---
{readme_content[:8000]}  # 限制长度，避免 token 超限
---

请提取部署步骤。
"""

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]

        try:
            response = await self.provider_router.chat_completion(
                messages=messages,
                temperature=0.2,  # 低温度，需要准确解析
                max_tokens=3000
            )

            # 解析 LLM 响应
            steps = self._parse_llm_response(response.content)
            return steps

        except Exception as e:
            logger.error(f"Failed to parse README with LLM: {e}")
            # 回退到规则解析
            return self._parse_readme_with_rules(readme_content, os_type)

    def _parse_llm_response(self, content: str) -> List[DeployStep]:
        """解析 LLM 响应"""
        import json
        import re

        # 尝试提取 JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                steps_data = data.get("steps", [])

                steps = []
                for i, step_data in enumerate(steps_data):
                    steps.append(DeployStep(
                        number=i + 1,
                        description=step_data.get("description", ""),
                        command=step_data.get("command")
                    ))
                return steps
            except json.JSONDecodeError:
                pass

        # 解析失败，返回空列表
        return []

    def _parse_readme_with_rules(
        self,
        readme_content: str,
        os_type: str
    ) -> List[DeployStep]:
        """使用规则解析 README (回退方案)"""
        steps = []
        step_number = 0

        # 常见的安装命令模式
        patterns = [
            # 包安装
            (r'`(apt-get install [^`]+)`', 'apt'),
            (r'`(apt install [^`]+)`', 'apt'),
            (r'`(yum install [^`]+)`', 'yum'),
            (r'`(dnf install [^`]+)`', 'dnf'),
            # Node.js
            (r'`(npm install[^`]*+)`', 'npm'),
            (r'`(yarn[^`]*+)`', 'yarn'),
            # Python
            (r'`(pip install [^`]+)`', 'pip'),
            (r'`(pip3 install [^`]+)`', 'pip'),
            # Docker
            (r'`(docker build[^`]*+)`', 'docker'),
            (r'`(docker run[^`]*+)`', 'docker'),
            (r'`(docker-compose[^`]*+)`', 'docker'),
            # 通用
            (r'`(make[^`]*+)`', 'build'),
            (r'`(cmake[^`]*+)`', 'build'),
        ]

        for pattern, step_type in patterns:
            matches = re.findall(pattern, readme_content, re.MULTILINE)
            for match in matches:
                step_number += 1
                steps.append(DeployStep(
                    number=step_number,
                    description=f"Execute {step_type} command",
                    command=match.strip('`')
                ))

        return steps

    def _identify_service_type(self, readme_content: str) -> str:
        """识别服务类型"""
        content_lower = readme_content.lower()

        # 关键词匹配
        if any(kw in content_lower for kw in ['react', 'vue', 'angular', 'frontend', 'ui']):
            return 'frontend'
        elif any(kw in content_lower for kw in ['django', 'flask', 'fastapi', 'express', 'spring']):
            return 'web'
        elif any(kw in content_lower for kw in ['database', 'mysql', 'postgres', 'mongo', 'redis']):
            return 'database'
        elif any(kw in content_lower for kw in ['docker', 'kubernetes', 'k8s']):
            return 'container'
        elif any(kw in content_lower for kw in ['nginx', 'apache', 'proxy']):
            return 'proxy'
        else:
            return 'web'  # 默认

    async def parse_baidu_tutorial(
        self,
        url: str,
        content: str,
        os_type: str = "ubuntu"
    ) -> DeployPlan:
        """解析百度经验/百家号教程"""
        # TODO: 实现百度教程解析
        logger.info(f"Parsing Baidu tutorial: {url}")
        return DeployPlan(
            github_url=url,
            service_type="web",
            steps=[]
        )

    async def parse_official_documentation(
        self,
        url: str,
        content: str,
        os_type: str = "ubuntu"
    ) -> DeployPlan:
        """解析官方文档"""
        # TODO: 实现官方文档解析
        logger.info(f"Parsing official documentation: {url}")
        return DeployPlan(
            github_url=url,
            service_type="web",
            steps=[]
        )
