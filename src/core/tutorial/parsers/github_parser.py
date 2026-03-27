"""
GitHub 解析器 - 解析 GitHub 仓库 README
"""

from typing import List, Dict, Any
import aiohttp
import re

from ..parser import BaseTutorialParser, ParsedTutorial, TutorialSource


class GitHubParser(BaseTutorialParser):
    """GitHub 解析器"""

    async def parse(self, url: str) -> ParsedTutorial:
        """解析 GitHub 仓库"""
        # 解析 URL
        # https://github.com/owner/repo
        # https://github.com/owner/repo/blob/main/README.md

        owner, repo = self._extract_owner_repo(url)
        readme_content = await self._fetch_readme(owner, repo)

        # 提取代码块
        code_blocks = self._extract_code_blocks(readme_content)

        # 使用 LLM 解析步骤（简化实现，实际应该调用 AI 服务）
        steps = self._extract_steps_simple(readme_content)

        return ParsedTutorial(
            source=TutorialSource.GITHUB,
            title=f"{owner}/{repo}",
            author=owner,
            content=readme_content,
            code_blocks=code_blocks,
            steps=steps,
            prerequisites=[],
            references=[url],
            raw_url=url,
        )

    def _extract_owner_repo(self, url: str) -> tuple:
        """提取 owner 和 repo"""
        pattern = r"github\.com[/:]([^/]+)/([^/]+?)(?:/|$)"
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2)
        raise ValueError(f"Invalid GitHub URL: {url}")

    async def _fetch_readme(self, owner: str, repo: str) -> str:
        """获取 README 内容"""
        # 尝试不同分支和文件名
        branches = ["main", "master"]
        filenames = ["README.md", "README", "readme.md"]

        for branch in branches:
            for filename in filenames:
                url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            return await resp.text()

        raise ValueError(f"README not found for {owner}/{repo}")

    def _extract_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """提取代码块"""
        code_blocks = []
        pattern = r"```(\w+)?\n(.*?)```"

        for match in re.finditer(pattern, content, re.DOTALL):
            language = match.group(1) or "text"
            code = match.group(2).strip()
            code_blocks.append({
                "language": language,
                "code": code,
                "is_shell": language in ["bash", "sh", "shell", "zsh"]
            })

        return code_blocks

    def _extract_steps_simple(self, content: str) -> List[Dict[str, Any]]:
        """简单提取步骤（基于 markdown 标题）"""
        steps = []
        step_number = 1

        # 匹配 ## 或 ### 标题
        heading_pattern = r'^#{2,3}\s+(.+)$'
        lines = content.split('\n')

        current_step = None
        step_content = []

        for line in lines:
            match = re.match(heading_pattern, line)
            if match:
                # 保存上一步
                if current_step:
                    steps.append({
                        "number": step_number - 1,
                        "description": current_step,
                        "content": '\n'.join(step_content),
                    })
                    step_number += 1

                current_step = match.group(1).strip()
                step_content = []
            elif current_step:
                step_content.append(line)

        # 保存最后一步
        if current_step:
            steps.append({
                "number": step_number,
                "description": current_step,
                "content": '\n'.join(step_content),
            })

        # 如果没有找到标题，尝试提取数字列表
        if not steps:
            list_pattern = r'^\d+\.\s+(.+)$'
            for line in lines:
                match = re.match(list_pattern, line)
                if match:
                    steps.append({
                        "number": len(steps) + 1,
                        "description": match.group(1).strip(),
                        "content": "",
                    })

        return steps or [{
            "number": 1,
            "description": "部署应用",
            "content": content[:500],
        }]
