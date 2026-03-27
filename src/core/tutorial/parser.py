"""
教程解析器 - 多来源支持
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class TutorialSource(str, Enum):
    """教程来源"""
    GITHUB = "github"
    BAIDU = "baidu"           # 百度经验/百家号
    CSDN = "csdn"
    JUEJIN = "juejin"
    OFFICIAL_DOC = "official_doc"
    UNKNOWN = "unknown"


class ParsedTutorial(BaseModel):
    """解析后的教程"""
    source: TutorialSource
    title: str
    author: Optional[str]
    content: str
    code_blocks: List[Dict[str, Any]]  # 代码块
    steps: List[Dict[str, Any]]        # 结构化步骤
    prerequisites: List[str]           # 前置条件
    references: List[str]              # 参考链接
    raw_url: str
    parsed_at: datetime = Field(default_factory=datetime.utcnow)


class BaseTutorialParser(ABC):
    """教程解析器基类"""

    @abstractmethod
    async def parse(self, url: str) -> ParsedTutorial:
        """解析教程"""
        pass


class TutorialParserRouter:
    """教程解析器路由器"""

    def __init__(self):
        self.parsers: Dict[TutorialSource, BaseTutorialParser] = {}
        self._register_default_parsers()

    def _register_default_parsers(self):
        """注册默认解析器"""
        from .parsers.github_parser import GitHubParser
        from .parsers.baidu_parser import BaiduParser
        from .parsers.official_doc_parser import OfficialDocParser

        self.parsers[TutorialSource.GITHUB] = GitHubParser()
        self.parsers[TutorialSource.BAIDU] = BaiduParser()
        self.parsers[TutorialSource.OFFICIAL_DOC] = OfficialDocParser()

    def detect_source(self, url: str) -> TutorialSource:
        """检测教程来源"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if "github.com" in domain:
            return TutorialSource.GITHUB
        elif "jingyan.baidu.com" in domain or "baijiahao.baidu.com" in domain:
            return TutorialSource.BAIDU
        elif "csdn.net" in domain:
            return TutorialSource.CSDN
        elif "juejin.cn" in domain:
            return TutorialSource.JUEJIN
        else:
            # 尝试作为官方文档处理
            return TutorialSource.OFFICIAL_DOC

    def get_parser(self, source: TutorialSource) -> BaseTutorialParser:
        """获取对应解析器"""
        parser = self.parsers.get(source)
        if not parser:
            logger.warning(f"No parser for source: {source}, using OfficialDocParser")
            return self.parsers[TutorialSource.OFFICIAL_DOC]
        return parser

    async def parse(self, url: str) -> ParsedTutorial:
        """解析教程"""
        source = self.detect_source(url)
        parser = self.get_parser(source)

        logger.info(f"Parsing tutorial from {source.value}: {url}")
        return await parser.parse(url)


# 全局路由器实例
_router: Optional[TutorialParserRouter] = None


def get_parser_router() -> TutorialParserRouter:
    """获取解析器路由器单例"""
    global _router
    if _router is None:
        _router = TutorialParserRouter()
    return _router
