"""
知识库检索模块测试
"""

import pytest
from src.core.knowledge.retriever import KnowledgeRetriever, KnowledgeSearchResult


class TestKnowledgeRetriever:
    """知识库检索测试类"""

    def test_search_by_keyword(self, db_session):
        """测试关键词检索"""
        from src.db.models import KnowledgeBase

        # 创建测试数据
        kb = KnowledgeBase(
            github_url_hash="test_hash_1",
            github_url="https://github.com/test/repo1",
            os_type="ubuntu",
            os_version="22.04",
            service_type="web",
            deploy_steps=[{"step": 1, "command": "apt update"}],
            common_errors=[],
            success_count=5,
            failure_count=1
        )
        db_session.add(kb)
        db_session.commit()

        # 执行检索
        retriever = KnowledgeRetriever(db_session)
        import asyncio
        results = asyncio.get_event_loop().run_until_complete(
            retriever.search(query="web", limit=10)
        )

        assert len(results) >= 1
        assert results[0].service_type == "web"

    def test_search_with_os_filter(self, db_session):
        """测试操作系统过滤"""
        from src.db.models import KnowledgeBase

        kb1 = KnowledgeBase(
            github_url_hash="hash_ubuntu",
            github_url="https://github.com/test/ubuntu-repo",
            os_type="ubuntu",
            os_version="22.04",
            service_type="web",
            deploy_steps=[],
            common_errors=[],
            success_count=3
        )
        kb2 = KnowledgeBase(
            github_url_hash="hash_centos",
            github_url="https://github.com/test/centos-repo",
            os_type="centos",
            os_version="7",
            service_type="web",
            deploy_steps=[],
            common_errors=[],
            success_count=2
        )
        db_session.add_all([kb1, kb2])
        db_session.commit()

        retriever = KnowledgeRetriever(db_session)
        import asyncio
        results = asyncio.get_event_loop().run_until_complete(
            retriever.search(query="web", os_filter="ubuntu", limit=10)
        )

        assert len(results) == 1
        assert results[0].os_type == "ubuntu"

    def test_search_similar(self, db_session):
        """测试相似案例检索"""
        from src.db.models import KnowledgeBase

        kb1 = KnowledgeBase(
            github_url_hash="hash_1",
            github_url="https://github.com/test/repo1",
            os_type="ubuntu",
            os_version="22.04",
            service_type="web",
            deploy_steps=[],
            common_errors=[],
            success_count=5
        )
        kb2 = KnowledgeBase(
            github_url_hash="hash_2",
            github_url="https://github.com/test/repo2",
            os_type="ubuntu",
            os_version="20.04",
            service_type="web",
            deploy_steps=[],
            common_errors=[],
            success_count=3
        )
        db_session.add_all([kb1, kb2])
        db_session.commit()

        retriever = KnowledgeRetriever(db_session)
        import asyncio
        results = asyncio.get_event_loop().run_until_complete(
            retriever.search_similar(
                github_url="https://github.com/test/repo1",
                os_type="ubuntu",
                service_type="web",
                limit=5
            )
        )

        assert len(results) >= 1
        assert results[0].github_url != "https://github.com/test/repo1"

    def test_calculate_similarity(self, db_session):
        """测试相似度计算"""
        retriever = KnowledgeRetriever(db_session)

        # 相同系统
        assert retriever._calculate_similarity("ubuntu", "ubuntu") == 1.0

        # Ubuntu 不同版本
        assert retriever._calculate_similarity("22.04", "20.04") == 0.8

        # 不同系统
        assert retriever._calculate_similarity("ubuntu", "centos") == 0.3

    def test_store_case_new(self, db_session):
        """测试存储新案例"""
        retriever = KnowledgeRetriever(db_session)
        import asyncio

        kb_id = asyncio.get_event_loop().run_until_complete(
            retriever.store_case(
                github_url="https://github.com/test/new-repo",
                os_type="ubuntu",
                os_version="22.04",
                service_type="web",
                deploy_steps=[{"step": 1, "command": "apt update"}],
                common_errors=[],
                success=True
            )
        )

        assert kb_id is not None

        # 验证存储
        from src.db.models import KnowledgeBase
        kb = db_session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        assert kb is not None
        assert kb.github_url == "https://github.com/test/new-repo"
        assert kb.success_count == 1

    def test_store_case_update(self, db_session):
        """测试更新现有案例"""
        import hashlib
        from src.db.models import KnowledgeBase

        # 计算 URL 哈希（与 store_case 方法一致）
        url_hash = hashlib.sha256("https://github.com/test/existing-repo".encode()).hexdigest()

        # 创建现有案例
        kb = KnowledgeBase(
            github_url_hash=url_hash,
            github_url="https://github.com/test/existing-repo",
            os_type="ubuntu",
            os_version="22.04",
            service_type="web",
            deploy_steps=[],
            common_errors=[],
            success_count=5,
            failure_count=2
        )
        db_session.add(kb)
        db_session.commit()

        retriever = KnowledgeRetriever(db_session)
        import asyncio

        # 存储成功案例（应增加 success_count）
        asyncio.get_event_loop().run_until_complete(
            retriever.store_case(
                github_url="https://github.com/test/existing-repo",
                os_type="ubuntu",
                os_version="22.04",
                service_type="web",
                deploy_steps=[],
                common_errors=[],
                success=True
            )
        )

        # 验证计数增加
        updated_kb = db_session.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb.id
        ).first()
        assert updated_kb.success_count == 6
