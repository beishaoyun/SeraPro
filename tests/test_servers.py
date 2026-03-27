"""
服务器管理 API 测试
"""

import pytest
from fastapi.testclient import TestClient


class TestServers:
    """服务器管理 API 测试类"""

    def test_list_servers_empty(self, client: TestClient, auth_token):
        """测试列出空服务器列表"""
        response = client.get(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_create_server(self, client, auth_token):
        """测试创建服务器"""
        response = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Test Server",
                "host": "192.168.1.100",
                "port": 22,
                "username": "root",
                "password": "server_password",
                "os_type": "ubuntu",
                "os_version": "22.04"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Server"
        assert data["host"] == "192.168.1.100"
        assert "id" in data

    def test_create_server_no_credentials(self, client, auth_token):
        """测试创建服务器缺少凭证"""
        response = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Test Server",
                "host": "192.168.1.100",
                "os_type": "ubuntu",
                "os_version": "22.04"
            }
        )
        assert response.status_code == 400

    def test_get_server(self, client, auth_token):
        """测试获取服务器详情"""
        # 先创建服务器
        create_response = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Test Server",
                "host": "192.168.1.100",
                "port": 22,
                "username": "root",
                "password": "server_password",
                "os_type": "ubuntu",
                "os_version": "22.04"
            }
        )
        server_id = create_response.json()["id"]

        # 获取服务器详情
        response = client.get(
            f"/api/v1/servers/{server_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["id"] == server_id

    def test_get_server_not_found(self, client, auth_token):
        """测试获取不存在的服务器"""
        response = client.get(
            "/api/v1/servers/99999",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404

    def test_update_server(self, client, auth_token):
        """测试更新服务器"""
        # 先创建服务器
        create_response = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Original Name",
                "host": "192.168.1.100",
                "port": 22,
                "username": "root",
                "password": "server_password",
                "os_type": "ubuntu",
                "os_version": "22.04"
            }
        )
        server_id = create_response.json()["id"]

        # 更新服务器
        response = client.put(
            f"/api/v1/servers/{server_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Updated Name",
                "host": "192.168.1.200",
                "port": 22,
                "username": "admin",
                "password": "new_password",
                "os_type": "ubuntu",
                "os_version": "24.04"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["host"] == "192.168.1.200"

    def test_delete_server(self, client, auth_token):
        """测试删除服务器"""
        # 先创建服务器
        create_response = client.post(
            "/api/v1/servers/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "To Delete",
                "host": "192.168.1.100",
                "port": 22,
                "username": "root",
                "password": "server_password",
                "os_type": "ubuntu",
                "os_version": "22.04"
            }
        )
        server_id = create_response.json()["id"]

        # 删除服务器
        response = client.delete(
            f"/api/v1/servers/{server_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 204

        # 验证已删除
        get_response = client.get(
            f"/api/v1/servers/{server_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 404

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/servers/")
        # FastAPI 返回 403 当缺少认证时
        assert response.status_code in [401, 403]
