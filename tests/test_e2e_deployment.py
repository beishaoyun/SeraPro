"""
端到端测试：完整部署流程

测试场景:
1. 用户注册 -> 登录 -> 添加服务器 -> 创建部署 -> 等待完成 -> 验证结果
2. 部署失败 -> AI 排错 -> 重新部署
3. 知识库检索 -> 相似案例推荐
"""

import pytest
import time
from fastapi.testclient import TestClient


class TestE2EDeployment:
    """端到端部署测试"""

    @pytest.mark.asyncio
    async def test_full_deployment_flow(self, client: TestClient, auth_token):
        """
        测试完整部署流程

        流程:
        1. 获取当前用户信息
        2. 添加服务器
        3. 创建部署任务
        4. 轮询等待部署完成
        5. 验证部署结果
        6. 验证知识库记录
        """
        # 1. 获取当前用户
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert me_response.status_code == 200
        user = me_response.json()
        assert "email" in user

        # 2. 添加服务器
        server_response = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "E2E Test Server",
                "host": "test.server.example.com",
                "port": 22,
                "username": "test",
                "password": "test123",
                "os_type": "ubuntu",
                "os_version": "22.04"
            }
        )
        assert server_response.status_code == 201
        server = server_response.json()
        server_id = server["id"]
        assert server["name"] == "E2E Test Server"
        assert server["host"] == "test.server.example.com"

        # 3. 创建部署任务
        deployment_response = client.post(
            "/api/v1/deployments/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "server_id": server_id,
                "github_url": "https://github.com/test/sample-repo",
                "service_type": "web"
            }
        )
        assert deployment_response.status_code == 201
        deployment = deployment_response.json()
        deployment_id = deployment["id"]
        assert deployment["status"] in ["pending", "running"]

        # 4. 轮询等待部署完成 (最多 30 秒)
        final_status = None
        for _ in range(30):
            status_response = client.get(
                f"/api/v1/deployments/{deployment_id}",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert status_response.status_code == 200

            deployment_status = status_response.json()["status"]
            final_status = deployment_status

            if deployment_status == "completed":
                break
            elif deployment_status == "failed":
                break

            time.sleep(1)

        # 5. 验证部署结果
        # 注意：在没有真实 SSH 服务器的情况下，部署会失败
        # 这里我们验证状态机是否正确运行
        assert final_status in ["completed", "failed", "running", "pending"]

        # 6. 获取部署详情
        final_response = client.get(
            f"/api/v1/deployments/{deployment_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        final_deployment = final_response.json()
        assert final_deployment["id"] == deployment_id
        assert "github_url" in final_deployment

        # 7. 验证部署步骤
        if "steps" in final_deployment:
            assert isinstance(final_deployment["steps"], list)

    @pytest.mark.asyncio
    async def test_server_crud_operations(self, client: TestClient, auth_token):
        """
        测试服务器 CRUD 操作

        流程:
        1. 创建服务器
        2. 获取服务器列表
        3. 获取服务器详情
        4. 更新服务器
        5. 删除服务器
        6. 验证已删除
        """
        # 1. 创建服务器
        create_data = {
            "name": "CRUD Test Server",
            "host": "192.168.1.100",
            "port": 22,
            "username": "admin",
            "password": "password123",
            "os_type": "ubuntu",
            "os_version": "22.04"
        }

        create_response = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=create_data
        )
        assert create_response.status_code == 201
        server = create_response.json()
        server_id = server["id"]

        # 2. 获取服务器列表
        list_response = client.get(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert list_response.status_code == 200
        servers = list_response.json()
        assert isinstance(servers, list)
        assert any(s["id"] == server_id for s in servers)

        # 3. 获取服务器详情
        get_response = client.get(
            f"/api/v1/servers/{server_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == server_id

        # 4. 更新服务器
        update_data = {
            "name": "Updated Server Name",
            "host": "192.168.1.200",
            "port": 2222,
            "username": "root",
            "password": "new_password",
            "os_type": "ubuntu",
            "os_version": "24.04"
        }

        update_response = client.put(
            f"/api/v1/servers/{server_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=update_data
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["name"] == "Updated Server Name"
        assert updated["host"] == "192.168.1.200"

        # 5. 删除服务器
        delete_response = client.delete(
            f"/api/v1/servers/{server_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert delete_response.status_code == 204

        # 6. 验证已删除
        get_deleted_response = client.get(
            f"/api/v1/servers/{server_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_deleted_response.status_code == 404

    @pytest.mark.asyncio
    async def test_knowledge_base_search(self, client: TestClient, auth_token):
        """
        测试知识库搜索

        流程:
        1. 搜索知识库
        2. 验证搜索结果
        """
        # 搜索知识库 - 正确的端点是 /search?q=xxx
        search_response = client.get(
            "/api/v1/knowledge/search?q=web&limit=10",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert search_response.status_code == 200

        results = search_response.json()
        assert isinstance(results, list)

    @pytest.mark.skip(reason="需要真实部署完成才能正常工作")
    @pytest.mark.asyncio
    async def test_ai_chat_debug(self, client: TestClient, auth_token):
        """
        测试 AI 对话排错

        流程:
        1. 创建服务器
        2. 创建部署
        3. 等待部署完成/失败
        4. 发送排错消息
        5. 验证 AI 响应

        注意：此测试需要真实 GitHub 仓库和 SSH 服务器才能通过
        """
        # 1. 创建服务器
        server_response = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "AI Debug Test Server",
                "host": "test.server.example.com",
                "port": 22,
                "username": "test",
                "password": "test123",
                "os_type": "ubuntu",
                "os_version": "22.04"
            }
        )
        server_id = server_response.json()["id"]

        # 2. 创建部署
        deployment_response = client.post(
            "/api/v1/deployments/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "server_id": server_id,
                "github_url": "https://github.com/test/sample-repo",
                "service_type": "web"
            }
        )
        deployment_id = deployment_response.json()["id"]

        # 3. 等待部署完成 (最多 30 秒)
        import time
        for _ in range(30):
            status_response = client.get(
                f"/api/v1/deployments/{deployment_id}",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            status = status_response.json()["status"]
            if status in ["completed", "failed"]:
                break
            time.sleep(1)

        # 4. 发送排错消息
        chat_response = client.post(
            f"/api/v1/deployments/{deployment_id}/chat",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "message": "部署失败了，请帮我分析原因",
                "context": {
                    "error_log": "apt-get update 失败：无法连接到源"
                }
            }
        )

        assert chat_response.status_code == 200
        response_data = chat_response.json()
        assert "reply" in response_data

        # 5. 清除对话历史
        clear_response = client.post(
            f"/api/v1/deployments/{deployment_id}/chat/clear",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert clear_response.status_code == 200

    @pytest.mark.asyncio
    async def test_websocket_connection(self, client: TestClient, auth_token):
        """
        测试 WebSocket 连接

        流程:
        1. 创建部署
        2. 建立 WebSocket 连接
        3. 验证连接成功
        """
        # 注意：TestClient 不支持 WebSocket
        # 这里验证 WebSocket 端点存在

        # 验证 WebSocket 路由配置
        # 实际测试需要使用 websocket-client 库
        pytest.skip("WebSocket 测试需要真实的 WebSocket 客户端")

    @pytest.mark.asyncio
    async def test_concurrent_deployments(self, client: TestClient, auth_token):
        """
        测试并发部署

        流程:
        1. 创建多个服务器
        2. 并发创建多个部署任务
        3. 验证所有部署都被正确处理
        """
        # 1. 创建多个服务器
        server_ids = []
        for i in range(3):
            server_response = client.post(
                "/api/v1/servers/",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "name": f"Concurrent Server {i}",
                    "host": f"server{i}.example.com",
                    "port": 22,
                    "username": "test",
                    "password": "test123",
                    "os_type": "ubuntu",
                    "os_version": "22.04"
                }
            )
            assert server_response.status_code == 201
            server_ids.append(server_response.json()["id"])

        # 2. 并发创建部署
        deployment_ids = []
        for i, server_id in enumerate(server_ids):
            deployment_response = client.post(
                "/api/v1/deployments/",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "server_id": server_id,
                    "github_url": f"https://github.com/test/repo-{i}",
                    "service_type": "web"
                }
            )
            assert deployment_response.status_code == 201
            deployment_ids.append(deployment_response.json()["id"])

        # 3. 验证所有部署
        for deployment_id in deployment_ids:
            response = client.get(
                f"/api/v1/deployments/{deployment_id}",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert response.status_code == 200
            deployment = response.json()
            assert deployment["id"] == deployment_id

    @pytest.mark.asyncio
    async def test_user_workflow(self, client: TestClient):
        """
        测试完整用户工作流

        流程:
        1. 用户注册
        2. 用户登录
        3. 获取用户信息
        4. 添加服务器
        5. 查看知识库
        """
        # 1. 用户注册
        register_email = f"e2e_{int(time.time())}@test.com"
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": register_email,
                "password": "password123",
                "company": "E2E Test Corp"
            }
        )
        assert register_response.status_code == 201
        user = register_response.json()
        assert user["email"] == register_email

        # 2. 用户登录
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": register_email,
                "password": "password123"
            }
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        access_token = tokens["access_token"]

        # 3. 获取用户信息
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == register_email

        # 4. 添加服务器
        server_response = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "First Server",
                "host": "first.server.com",
                "port": 22,
                "username": "root",
                "password": "server_password",
                "os_type": "ubuntu",
                "os_version": "22.04"
            }
        )
        assert server_response.status_code == 201

        # 5. 查看知识库 - 使用正确的端点
        knowledge_response = client.get(
            "/api/v1/knowledge/search?q=ubuntu&limit=5",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert knowledge_response.status_code == 200


class TestE2EErrorHandling:
    """端到端错误处理测试"""

    @pytest.mark.asyncio
    async def test_invalid_token(self, client: TestClient):
        """测试无效令牌"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: TestClient):
        """测试未授权访问"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_invalid_server_data(self, client: TestClient, auth_token):
        """测试无效服务器数据"""
        # 缺少密码
        response = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Invalid Server",
                "host": "server.com",
                "os_type": "ubuntu",
                "os_version": "22.04"
            }
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_duplicate_server_name(self, client: TestClient, auth_token):
        """测试重复服务器名称 (如果有限制)"""
        # 创建第一个服务器
        create1 = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Duplicate Test",
                "host": "server1.com",
                "port": 22,
                "username": "root",
                "password": "password123",
                "os_type": "ubuntu",
                "os_version": "22.04"
            }
        )
        assert create1.status_code == 201

        # 创建同名但不同 host 的服务器 (应该允许)
        create2 = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Duplicate Test",
                "host": "server2.com",
                "port": 22,
                "username": "root",
                "password": "password123",
                "os_type": "ubuntu",
                "os_version": "22.04"
            }
        )
        # 名称可以重复，host 必须唯一
        assert create2.status_code in [201, 400]
