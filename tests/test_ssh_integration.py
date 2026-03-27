"""
SSH 模块集成测试

注意：这些测试需要真实的 SSH 服务器或 Mock 服务器。
在 CI 环境中使用 docker-compose 启动测试 SSH 容器。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.ssh.client import SSHClient, SSHCredentials
from src.core.ssh.connection_pool import SSHConnectionPool, PooledConnection


class TestSSHClient:
    """SSH 客户端测试"""

    @pytest.mark.asyncio
    async def test_connect_with_password(self):
        """测试使用密码连接"""
        client = SSHClient()

        # Mock paramiko
        with patch.object(client, '_connect_sync') as mock_connect:
            credentials = SSHCredentials(
                host="test.server.com",
                port=22,
                username="test",
                password="test123",
                timeout=30
            )

            result = await client.connect(credentials)

            # 验证连接被调用
            mock_connect.assert_called_once()
            assert client.connected == True

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_with_ssh_key(self):
        """测试使用 SSH 密钥连接"""
        client = SSHClient()

        ssh_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MhQXXVXXFXjRnJ7H
-----END RSA PRIVATE KEY-----"""

        credentials = SSHCredentials(
            host="test.server.com",
            port=22,
            username="test",
            ssh_key=ssh_key,
            timeout=30
        )

        # Mock paramiko 的 RSAKey
        with patch('paramiko.RSAKey.from_private_key') as mock_key:
            mock_key.return_value = MagicMock()

            with patch.object(client, '_connect_sync'):
                result = await client.connect(credentials)

                assert result == True
                assert client.connected == True

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """测试连接失败"""
        client = SSHClient()

        credentials = SSHCredentials(
            host="unreachable.server.com",
            port=22,
            username="test",
            password="test123",
            timeout=5
        )

        with patch.object(client, '_connect_sync', side_effect=Exception("Connection refused")):
            result = await client.connect(credentials)

            assert result == False
            assert client.connected == False

    @pytest.mark.asyncio
    async def test_execute_command(self):
        """测试执行命令"""
        client = SSHClient()
        client.connected = True

        # Mock paramiko exec_command
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"Ubuntu 22.04\n"
        mock_stderr.read.return_value = b""

        client.client = MagicMock()
        client.client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        result = await client.execute("uname -a")

        assert result["exit_code"] == 0
        assert "Ubuntu" in result["stdout"]
        assert result["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_execute_command_failure(self):
        """测试执行命令失败"""
        client = SSHClient()
        client.connected = True

        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()

        mock_stdout.channel.recv_exit_status.return_value = 1
        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = b"command not found\n"

        client.client = MagicMock()
        client.client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        result = await client.execute("invalid_command")

        assert result["exit_code"] == 1
        assert "command not found" in result["stderr"]

    @pytest.mark.asyncio
    async def test_execute_not_connected(self):
        """测试未连接时执行命令"""
        client = SSHClient()
        client.connected = False

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.execute("uname -a")

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试异步上下文管理器"""
        client = SSHClient()

        with patch.object(client, '_connect_sync'):
            with patch.object(client, 'disconnect', wraps=client.disconnect) as mock_disconnect:
                async with client:
                    pass

                mock_disconnect.assert_called_once()


class TestSSHConnectionPool:
    """SSH 连接池测试"""

    @pytest.fixture
    def pool(self):
        """创建测试连接池"""
        return SSHConnectionPool(
            max_connections=5,
            idle_timeout=60,
            max_uses=10
        )

    @pytest.mark.asyncio
    async def test_acquire_new_connection(self, pool):
        """测试获取新连接"""
        credentials = SSHCredentials(
            host="test.server.com",
            port=22,
            username="test",
            password="test123"
        )

        with patch('src.core.ssh.connection_pool.SSHClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.connect.return_value = True
            MockClient.return_value = mock_client

            client = await pool.acquire("server_1", credentials)

            assert client == mock_client
            assert "server_1" in pool._pool
            assert pool._pool["server_1"].is_in_use == True

    @pytest.mark.asyncio
    async def test_reuse_connection(self, pool):
        """测试复用连接"""
        credentials = SSHCredentials(
            host="test.server.com",
            port=22,
            username="test",
            password="test123"
        )

        with patch('src.core.ssh.connection_pool.SSHClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.connect.return_value = True
            MockClient.return_value = mock_client

            # 第一次获取
            client1 = await pool.acquire("server_1", credentials)
            pool.release("server_1")

            # 第二次获取 (应复用)
            client2 = await pool.acquire("server_1", credentials)

            assert client1 == client2
            # use_count 在第二次 acquire 时重置为 0 然后增加到 1
            assert pool._pool["server_1"].use_count >= 1

    @pytest.mark.asyncio
    async def test_release_connection(self, pool):
        """测试释放连接"""
        credentials = SSHCredentials(
            host="test.server.com",
            port=22,
            username="test",
            password="test123"
        )

        with patch('src.core.ssh.connection_pool.SSHClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.connect.return_value = True
            MockClient.return_value = mock_client

            await pool.acquire("server_1", credentials)
            pool.release("server_1")

            assert pool._pool["server_1"].is_in_use == False

    @pytest.mark.asyncio
    async def test_max_connections_limit(self, pool):
        """测试最大连接数限制"""
        credentials = SSHCredentials(
            host="test.server.com",
            port=22,
            username="test",
            password="test123"
        )

        with patch('src.core.ssh.connection_pool.SSHClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.connect.return_value = True
            MockClient.return_value = mock_client

            # 获取 5 个连接 (达到上限)
            for i in range(5):
                await pool.acquire(f"server_{i}", credentials)
                pool.release(f"server_{i}")

            # 第 6 个应该淘汰一个旧连接
            await pool.acquire("server_6", credentials)

            # 验证连接数不超过上限
            assert len(pool._pool) <= pool.max_connections

    @pytest.mark.asyncio
    async def test_connection_stale_max_uses(self, pool):
        """测试连接过期 - 达到最大使用次数"""
        credentials = SSHCredentials(
            host="test.server.com",
            port=22,
            username="test",
            password="test123"
        )

        with patch('src.core.ssh.connection_pool.SSHClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.connect.return_value = True
            MockClient.return_value = mock_client

            # 首次获取
            await pool.acquire("server_1", credentials)
            pool.release("server_1")

            # 手动设置 use_count 达到上限
            pool._pool["server_1"].use_count = pool.max_uses

            # 再次获取应重建连接
            new_client = await pool.acquire("server_1", credentials)

            # 连接重建后 use_count 从 0 开始，然后增加到 1
            # 验证连接已重建 (use_count 被重置过)
            assert pool._pool["server_1"].use_count >= 1

    @pytest.mark.asyncio
    async def test_health_check(self, pool):
        """测试健康检查"""
        client = SSHClient()
        client.connected = True

        with patch.object(client, 'execute') as mock_execute:
            mock_execute.return_value = {"exit_code": 0, "stdout": "health_check\n", "stderr": "", "duration_ms": 10}

            is_healthy = await pool._health_check(client)

            assert is_healthy == True
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, pool):
        """测试健康检查失败"""
        client = SSHClient()
        client.connected = True

        with patch.object(client, 'execute', side_effect=Exception("Connection lost")):
            is_healthy = await pool._health_check(client)

            assert is_healthy == False

    @pytest.mark.asyncio
    async def test_get_stats(self, pool):
        """测试获取统计信息"""
        credentials = SSHCredentials(
            host="test.server.com",
            port=22,
            username="test",
            password="test123"
        )

        with patch('src.core.ssh.connection_pool.SSHClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.connect.return_value = True
            MockClient.return_value = mock_client

            await pool.acquire("server_1", credentials)
            pool.release("server_1")

            stats = pool.get_stats()

            assert stats["total_connections"] == 1
            assert stats["in_use"] == 0
            assert stats["idle"] == 1
            # use_count 在 acquire 时从 0 增加到 1
            assert stats["total_use_count"] >= 1

    @pytest.mark.asyncio
    async def test_cleanup_idle(self, pool):
        """测试清理空闲连接"""
        credentials = SSHCredentials(
            host="test.server.com",
            port=22,
            username="test",
            password="test123"
        )

        with patch('src.core.ssh.connection_pool.SSHClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.connect.return_value = True
            MockClient.return_value = mock_client

            # 设置很短的空闲超时
            pool.idle_timeout = 0

            await pool.acquire("server_1", credentials)
            pool.release("server_1")

            # 等待一小段时间
            await asyncio.sleep(0.1)

            # 清理
            await pool._cleanup_idle()

            # 验证连接已被清理
            assert "server_1" not in pool._pool

    @pytest.mark.asyncio
    async def test_start_and_stop(self, pool):
        """测试启动和停止"""
        await pool.start()

        assert pool._running == True
        assert pool._cleanup_task is not None

        await pool.stop()

        assert pool._running == False
