"""
WebSocket 连接管理器

功能:
- 管理部署日志的 WebSocket 连接
- 实时推送部署步骤执行日志
- 支持多个客户端同时订阅
"""

from typing import Dict, Set, Any
from fastapi import WebSocket
import logging
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # deployment_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, deployment_id: int):
        """接受 WebSocket 连接并订阅指定部署"""
        await websocket.accept()

        if deployment_id not in self.active_connections:
            self.active_connections[deployment_id] = set()

        self.active_connections[deployment_id].add(websocket)
        logger.info(f"WebSocket connected for deployment {deployment_id}")

    def disconnect(self, websocket: WebSocket, deployment_id: int):
        """断开 WebSocket 连接"""
        if deployment_id in self.active_connections:
            self.active_connections[deployment_id].discard(websocket)

            if not self.active_connections[deployment_id]:
                del self.active_connections[deployment_id]

        logger.info(f"WebSocket disconnected for deployment {deployment_id}")

    async def send_personal_message(self, message: dict, deployment_id: int):
        """向指定部署的所有订阅者发送消息"""
        if deployment_id in self.active_connections:
            disconnected = set()

            for connection in self.active_connections[deployment_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send message to WebSocket: {e}")
                    disconnected.add(connection)

            # 清理断开的连接
            for conn in disconnected:
                self.active_connections[deployment_id].discard(conn)

    async def broadcast_deployment_update(self, deployment_id: int, data: dict):
        """广播部署更新"""
        message = {
            "type": "deployment_update",
            "deployment_id": deployment_id,
            "data": data
        }
        await self.send_personal_message(message, deployment_id)

    async def broadcast_step_log(self, deployment_id: int, step_number: int, log: dict):
        """广播步骤执行日志"""
        message = {
            "type": "step_log",
            "deployment_id": deployment_id,
            "step_number": step_number,
            "log": log
        }
        await self.send_personal_message(message, deployment_id)

    async def broadcast_deployment_complete(self, deployment_id: int, success: bool, error_message: str = None):
        """广播部署完成"""
        message = {
            "type": "deployment_complete",
            "deployment_id": deployment_id,
            "success": success,
            "error_message": error_message
        }
        await self.send_personal_message(message, deployment_id)


# 单例
manager = ConnectionManager()
