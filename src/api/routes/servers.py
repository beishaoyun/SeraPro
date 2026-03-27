"""
服务器管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
import json
import logging

from src.db.database import get_db
from src.db.models import Server, User
from src.api.routes.auth import get_current_user
from src.core.credentials.encryption import CredentialEncryptor
from src.core.ssh.client import SSHClient, SSHCredentials
from src.config import settings

logger = logging.getLogger(__name__)

# 初始化加密器
encryptor = CredentialEncryptor(settings.MASTER_KEY.encode())

router = APIRouter()


# =========== Schemas ===========

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ServerCreate(BaseModel):
    """创建服务器请求"""
    name: str = Field(..., description="服务器名称")
    host: str = Field(..., description="服务器 IP 或域名")
    port: int = Field(default=22, description="SSH 端口")
    username: str = Field(default="root", description="SSH 用户名")
    password: Optional[str] = Field(None, description="SSH 密码")
    ssh_key: Optional[str] = Field(None, description="SSH 私钥")
    os_type: str = Field(..., description="操作系统类型")
    os_version: str = Field(..., description="操作系统版本")


class ServerResponse(BaseModel):
    """服务器响应"""
    id: int
    name: str
    host: str
    port: int
    username: Optional[str] = None  # 从凭证中提取的用户名
    os_type: str
    os_version: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServerTestResponse(BaseModel):
    """SSH 连接测试响应"""
    success: bool
    message: str
    os_info: Optional[str] = None


# =========== API Endpoints ===========

@router.get("/", response_model=List[ServerResponse])
async def list_servers(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """列出用户的所有服务器"""
    servers = db.query(Server).filter(
        Server.user_id == current_user.id
    ).offset(skip).limit(limit).all()

    return servers


@router.post("/", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(
    server_data: ServerCreate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    添加服务器

    - **name**: 服务器名称
    - **host**: 服务器 IP 或域名
    - **port**: SSH 端口 (默认 22)
    - **username**: SSH 用户名 (默认 root)
    - **password**: SSH 密码 (与 ssh_key 二选一)
    - **ssh_key**: SSH 私钥 (与 password 二选一)
    - **os_type**: 操作系统类型 (ubuntu, centos, debian 等)
    - **os_version**: 操作系统版本 (22.04, 8, 11 等)
    """
    # 验证凭证
    if not server_data.password and not server_data.ssh_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either password or ssh_key is required"
        )

    # 加密凭证
    credentials_data = {
        "username": server_data.username,
        "password": server_data.password,
        "ssh_key": server_data.ssh_key
    }
    encrypted_credentials = encryptor.encrypt_base64(
        json.dumps(credentials_data)
    )

    new_server = Server(
        user_id=current_user.id,
        name=server_data.name,
        host=server_data.host,
        port=server_data.port,
        auth_type="password" if server_data.password else "ssh_key",
        credentials=encrypted_credentials,
        os_type=server_data.os_type,
        os_version=server_data.os_version,
        status="active"
    )

    db.add(new_server)
    db.commit()
    db.refresh(new_server)

    logger.info(f"Server created: {new_server.name} ({new_server.host})")
    return new_server


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """获取服务器详情"""
    server = db.query(Server).filter(
        Server.id == server_id,
        Server.user_id == current_user.id
    ).first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    return server


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: int,
    server_data: ServerCreate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """更新服务器信息"""
    server = db.query(Server).filter(
        Server.id == server_id,
        Server.user_id == current_user.id
    ).first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    # 更新字段
    server.name = server_data.name
    server.host = server_data.host
    server.port = server_data.port
    server.os_type = server_data.os_type
    server.os_version = server_data.os_version

    # 更新凭证 (如果提供)
    if server_data.password or server_data.ssh_key:
        credentials_data = {
            "username": server_data.username,
            "password": server_data.password,
            "ssh_key": server_data.ssh_key
        }
        server.credentials = encryptor.encrypt_base64(
            json.dumps(credentials_data)
        )
        server.auth_type = "password" if server_data.password else "ssh_key"

    db.commit()
    db.refresh(server)

    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """删除服务器"""
    server = db.query(Server).filter(
        Server.id == server_id,
        Server.user_id == current_user.id
    ).first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    db.delete(server)
    db.commit()

    logger.info(f"Server deleted: {server.name}")
    return None


@router.post("/{server_id}/test-connection", response_model=ServerTestResponse)
async def test_connection(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """测试 SSH 连接"""
    server = db.query(Server).filter(
        Server.id == server_id,
        Server.user_id == current_user.id
    ).first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    # 解密凭证
    try:
        credentials_json = encryptor.decrypt_base64(server.credentials)
        credentials_data = json.loads(credentials_json)
    except Exception as e:
        logger.error(f"Failed to decrypt credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_ERROR,
            detail="Failed to decrypt server credentials"
        )

    # 创建 SSH 凭证
    ssh_creds = SSHCredentials(
        host=server.host,
        port=server.port,
        username=credentials_data.get("username", "root"),
        password=credentials_data.get("password"),
        ssh_key=credentials_data.get("ssh_key")
    )

    # 测试连接
    client = SSHClient()
    try:
        success = await client.connect(ssh_creds)
        if success:
            # 获取系统信息
            result = await client.execute("uname -a")
            os_info = result.get("stdout", "").strip()[:200]
            return ServerTestResponse(
                success=True,
                message=f"Successfully connected to {server.host}:{server.port}",
                os_info=os_info
            )
        else:
            return ServerTestResponse(
                success=False,
                message=f"Failed to connect to {server.host}:{server.port}"
            )
    except Exception as e:
        logger.error(f"SSH connection test failed: {e}")
        return ServerTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )
    finally:
        await client.disconnect()
