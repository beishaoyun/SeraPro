"""
官方文档解析器 - 通用网页解析
"""

from typing import List, Dict, Any
import aiohttp
from bs4 import BeautifulSoup
import logging

from ..parser import BaseTutorialParser, ParsedTutorial, TutorialSource

logger = logging.getLogger(__name__)


class OfficialDocParser(BaseTutorialParser):
    """官方文档解析器"""

    def __init__(self, use_browser: bool = False):
        self.use_browser = use_browser  # 对于 SPA 网站需要使用浏览器

    async def parse(self, url: str) -> ParsedTutorial:
        """解析官方文档"""
        html = await self._fetch_html(url)

        soup = BeautifulSoup(html, "html.parser")

        title = soup.find("title").get_text(strip=True) if soup.find("title") else "无标题"
        content = self._extract_main_content(soup)
        code_blocks = self._extract_code_blocks(soup)
        steps = self._extract_steps(content)

        return ParsedTutorial(
            source=TutorialSource.OFFICIAL_DOC,
            title=title,
            author=None,
            content=content,
            code_blocks=code_blocks,
            steps=steps,
            prerequisites=[],
            references=[url],
            raw_url=url,
        )

    async def _fetch_html(self, url: str) -> str:
        """获取页面 HTML"""
        if self.use_browser:
            return await self._fetch_with_browser(url)
        else:
            return await self._fetch_with_http(url)

    async def _fetch_with_browser(self, url: str) -> str:
        """使用浏览器获取页面（支持 JavaScript 渲染）"""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url)
                html = await page.content()
                await browser.close()
                return html
        except ImportError:
            logger.warning("Playwright not installed, falling back to HTTP fetch")
            return await self._fetch_with_http(url)

    async def _fetch_with_http(self, url: str) -> str:
        """直接 HTTP 获取"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                return await resp.text()

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """提取主要内容"""
        # 尝试常见容器
        for selector in ["article", "main", ".content", ".main", "#content", ".doc-content", ".documentation"]:
            elem = soup.select_one(selector)
            if elem:
                # 清理不需要的内容
                for tag in elem(["script", "style", "nav", "header", "footer", "aside"]):
                    tag.decompose()
                return elem.get_text("\n", strip=True)

        # 回退：获取整个 body
        body = soup.find("body")
        return body.get_text("\n", strip=True) if body else ""

    def _extract_code_blocks(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """提取代码块"""
        code_blocks = []

        for pre in soup.find_all("pre"):
            code_elem = pre.find("code")
            if code_elem:
                classes = code_elem.get("class", [])
                language = "text"
                for cls in classes:
                    if cls.startswith("language-"):
                        language = cls.replace("language-", "")
                        break
                    elif cls in ["bash", "shell", "python", "javascript", "json", "yaml", "yml"]:
                        language = cls
                        break

                code = code_elem.get_text(strip=True)
            else:
                language = "text"
                code = pre.get_text(strip=True)

            if code:  # 只添加非空代码块
                code_blocks.append({
                    "language": language,
                    "code": code,
                    "is_shell": language in ["bash", "shell", "sh"]
                })

        return code_blocks

    def _extract_steps(self, content: str) -> List[Dict[str, Any]]:
        """提取步骤"""
        steps = []
        import re

        # 匹配常见步骤格式
        patterns = [
            r'(?:Step|步骤)\s*\d*[：:.\)]\s*([^\n]+)',
            r'^\d+[、.]\s*([^\n]+)',
            r'(?:首先 | 然后 | 接着 | 最后)[，,]?\s*([^\n]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                for i, match in enumerate(matches):
                    steps.append({
                        "number": i + 1,
                        "description": match.strip()[:200],
                        "content": "",
                    })
                break

        # 如果没有找到步骤，返回默认步骤
        if not steps:
            steps.append({
                "number": 1,
                "description": "参考文档内容部署",
                "content": content[:500],
            })

        return steps
