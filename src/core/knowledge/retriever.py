"""
RAG 知识库检索模块

功能:
- 向量相似度检索
- 关键词检索
- 混合检索策略
- 检索结果 rerank
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class KnowledgeSearchResult(BaseModel):
    """知识库搜索结果"""
    id: int
    github_url: str
    os_type: str
    os_version: str
    service_type: str
    deploy_steps: List[Dict]
    common_errors: List[Dict]
    success_count: int
    failure_count: int
    similarity_score: float
    relevance_score: float


class KnowledgeRetriever:
    """知识库检索器"""

    def __init__(self, db_session):
        self.db = db_session

    async def search(
        self,
        query: str,
        os_filter: Optional[str] = None,
        service_type: Optional[str] = None,
        limit: int = 10
    ) -> List[KnowledgeSearchResult]:
        """
        搜索知识库

        Args:
            query: 搜索查询
            os_filter: 操作系统过滤
            service_type: 服务类型过滤
            limit: 返回数量限制

        Returns:
            搜索结果列表
        """
        from src.db.models import KnowledgeBase
        from sqlalchemy import or_

        # 构建查询
        query_obj = self.db.query(KnowledgeBase)

        # 关键词检索
        query_obj = query_obj.filter(
            or_(
                KnowledgeBase.github_url.ilike(f"%{query}%"),
                KnowledgeBase.service_type.ilike(f"%{query}%")
            )
        )

        # 过滤条件
        if os_filter:
            query_obj = query_obj.filter(KnowledgeBase.os_type == os_filter)
        if service_type:
            query_obj = query_obj.filter(KnowledgeBase.service_type == service_type)

        # 按成功数排序
        query_obj = query_obj.order_by(
            KnowledgeBase.success_count.desc(),
            KnowledgeBase.created_at.desc()
        )

        # 执行查询
        results = query_obj.limit(limit).all()

        return [
            KnowledgeSearchResult(
                id=r.id,
                github_url=r.github_url,
                os_type=r.os_type,
                os_version=r.os_version,
                service_type=r.service_type,
                deploy_steps=r.deploy_steps,
                common_errors=r.common_errors,
                success_count=r.success_count,
                failure_count=r.failure_count,
                similarity_score=0.0,  # 关键词检索没有相似度分数
                relevance_score=self._calculate_relevance(r, query)
            )
            for r in results
        ]

    async def search_similar(
        self,
        github_url: str,
        os_type: str,
        service_type: str,
        limit: int = 5
    ) -> List[KnowledgeSearchResult]:
        """
        搜索相似案例

        Args:
            github_url: GitHub 项目地址
            os_type: 操作系统类型
            service_type: 服务类型
            limit: 返回数量限制

        Returns:
            相似案例列表
        """
        from src.db.models import KnowledgeBase

        # 搜索相同服务类型的案例
        results = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.service_type == service_type,
            KnowledgeBase.github_url != github_url
        ).order_by(
            KnowledgeBase.success_count.desc()
        ).limit(limit).all()

        return [
            KnowledgeSearchResult(
                id=r.id,
                github_url=r.github_url,
                os_type=r.os_type,
                os_version=r.os_version,
                service_type=r.service_type,
                deploy_steps=r.deploy_steps,
                common_errors=r.common_errors,
                success_count=r.success_count,
                failure_count=r.failure_count,
                similarity_score=self._calculate_similarity(os_type, r.os_type),
                relevance_score=0.5
            )
            for r in results
        ]

    def _calculate_relevance(self, knowledge: Any, query: str) -> float:
        """计算相关性分数"""
        score = 0.5  # 基础分数

        # GitHub URL 匹配
        if query.lower() in knowledge.github_url.lower():
            score += 0.3

        # 服务类型匹配
        if query.lower() in knowledge.service_type.lower():
            score += 0.2

        # 成功案例权重
        if knowledge.success_count > 0:
            score += min(0.2, knowledge.success_count * 0.02)

        return min(1.0, score)

    def _calculate_similarity(self, query_os: str, target_os: str) -> float:
        """计算操作系统相似度"""
        if query_os == target_os:
            return 1.0

        # 同系列操作系统
        ubuntu_versions = ["18.04", "20.04", "22.04", "24.04"]
        centos_versions = ["7", "8", "9"]
        debian_versions = ["10", "11", "12"]

        if query_os in ubuntu_versions and target_os in ubuntu_versions:
            return 0.8
        if query_os in centos_versions and target_os in centos_versions:
            return 0.8
        if query_os in debian_versions and target_os in debian_versions:
            return 0.8

        return 0.3

    async def store_case(
        self,
        github_url: str,
        os_type: str,
        os_version: str,
        service_type: str,
        deploy_steps: List[Dict],
        common_errors: List[Dict],
        success: bool
    ) -> int:
        """
        存储部署案例到知识库

        Args:
            github_url: GitHub 项目地址
            os_type: 操作系统类型
            os_version: 操作系统版本
            service_type: 服务类型
            deploy_steps: 部署步骤
            common_errors: 常见错误
            success: 是否成功

        Returns:
            知识库条目 ID
        """
        import hashlib
        from src.db.models import KnowledgeBase

        # 计算 URL 哈希
        url_hash = hashlib.sha256(github_url.encode()).hexdigest()

        # 查找现有条目
        existing = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.github_url_hash == url_hash,
            KnowledgeBase.os_type == os_type,
            KnowledgeBase.os_version == os_version
        ).first()

        if existing:
            # 更新现有条目
            existing.deploy_steps = deploy_steps
            if success:
                existing.success_count += 1
            else:
                existing.failure_count += 1
            self.db.commit()
            self.db.refresh(existing)
            return existing.id
        else:
            # 创建新条目
            new_entry = KnowledgeBase(
                github_url_hash=url_hash,
                github_url=github_url,
                os_type=os_type,
                os_version=os_version,
                service_type=service_type,
                deploy_steps=deploy_steps,
                common_errors=common_errors,
                success_count=1 if success else 0,
                failure_count=0 if success else 1
            )
            self.db.add(new_entry)
            self.db.commit()
            self.db.refresh(new_entry)
            return new_entry.id
