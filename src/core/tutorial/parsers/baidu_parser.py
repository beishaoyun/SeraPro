"""
百度经验/百家号解析器
"""

from typing import List, Dict, Any
import aiohttp
from bs4 import BeautifulSoup
import re

from ..parser import BaseTutorialParser, ParsedTutorial, TutorialSource


class BaiduParser(BaseTutorialParser):
    """百度解析器"""

    async def parse(self, url: str) -> ParsedTutorial:
        """解析百度经验/百家号"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                html = await resp.text(encoding="utf-8")

        soup = BeautifulSoup(html, "html.parser")

        # 提取标题
        title = self._extract_title(soup, url)

        # 提取内容
        content = self._extract_content(soup, url)

        # 提取代码块
        code_blocks = self._extract_code_blocks(content)

        # 提取步骤
        steps = self._extract_steps(content)

        return ParsedTutorial(
            source=TutorialSource.BAIDU,
            title=title,
            author=self._extract_author(soup, url),
            content=content,
            code_blocks=code_blocks,
            steps=steps,
            prerequisites=[],
            references=[url],
            raw_url=url,
        )

    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """提取标题"""
        if "jingyan.baidu.com" in url:
            title_tag = soup.find("h1", class_="title-name")
        else:  # 百家号
            title_tag = soup.find("h1", class_="article-title")

        return title_tag.get_text(strip=True) if title_tag else "无标题"

    def _extract_author(self, soup: BeautifulSoup, url: str) -> str:
        """提取作者"""
        if "jingyan.baidu.com" in url:
            author_tag = soup.find("div", class_="user-name")
        else:
            author_tag = soup.find("a", class_="author-name")

        return author_tag.get_text(strip=True) if author_tag else "未知"

    def _extract_content(self, soup: BeautifulSoup, url: str) -> str:
        """提取正文内容"""
        if "jingyan.baidu.com" in url:
            # 百度经验
            content_div = soup.find("div", class_="exp-content")
            if not content_div:
                content_div = soup.find("div", id="exp-content")
        else:
            # 百家号
            content_div = soup.find("div", class_="article-content")

        if content_div:
            # 去除 script, style 等
            for tag in content_div(["script", "style", "iframe", "nav", "header", "footer"]):
                tag.decompose()
            return content_div.get_text("\n", strip=True)

        return ""

    def _extract_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """提取代码块（百度通常没有格式化的代码块，需要启发式识别）"""
        code_blocks = []
        lines = content.split("\n")

        # 简单启发式：识别命令行
        for line in lines:
            line = line.strip()
            if line.startswith("$ ") or line.startswith("# "):
                code_blocks.append({
                    "language": "bash",
                    "code": line.lstrip("$ #").strip(),
                    "is_shell": True
                })
            elif re.match(r"^(apt|yum|pip|npm|docker|kubectl|cd|mkdir|rm|cp|mv|curl|wget)\s", line):
                code_blocks.append({
                    "language": "bash",
                    "code": line,
                    "is_shell": True
                })

        return code_blocks

    def _extract_steps(self, content: str) -> List[Dict[str, Any]]:
        """提取步骤"""
        steps = []

        # 尝试匹配 "步骤 X" 或 "第一步" 等模式
        step_patterns = [
            r'(?:步骤 | 第 [一二三四五六七八九十]+ 步)[：:]\s*(.+?)(?=\n步骤 | 第 |$)',
            r'(\d+[、.]\s*[^\n]+)',
        ]

        for pattern in step_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                for i, match in enumerate(matches):
                    steps.append({
                        "number": i + 1,
                        "description": match.strip()[:200],
                        "content": "",
                    })
                break

        # 如果没有找到步骤，返回空列表
        if not steps:
            steps.append({
                "number": 1,
                "description": "按照教程内容部署",
                "content": content[:500],
            })

        return steps
