"""
部署管理 API

功能:
- 创建部署任务
- 自动解析 GitHub README 生成部署计划
- 串行执行部署步骤
- 实时日志记录
- AI 智能排错
- 知识库自动记录
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, WebSocket, WebSocketDisconnect, Query
from typing import List, Optional, Dict
from datetime import datetime
import logging
import aiohttp
import json

from src.db.database import get_db
from src.db.models import Deployment, DeploymentStep, Server, User
from src.api.routes.auth import get_current_user
from src.core.ssh.client import SSHClient, SSHCredentials
from src.core.deployment.executor import DeployExecutor, DeployPlan, DeployStep as ExecutorDeployStep
from src.core.deployment.planner import DeployPlanner
from src.core.ai.providers.router import ProviderRouter
from src.core.knowledge.retriever import KnowledgeRetriever
from src.core.ai.debugger import AIDebugger
from src.core.credentials.encryption import CredentialEncryptor
from src.core.websocket.manager import manager as websocket_manager
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化组件
encryptor = CredentialEncryptor(settings.MASTER_KEY.encode())


# =========== Schemas ===========

from pydantic import BaseModel, Field


class DeploymentCreate(BaseModel):
    """创建部署请求"""
    server_id: int = Field(..., description="服务器 ID")
    github_url: str = Field(..., description="GitHub 项目地址")
    service_type: Optional[str] = Field(None, description="服务类型 (可选，会自动识别)")


class DeploymentResponse(BaseModel):
    """部署响应"""
    id: int
    user_id: int
    server_id: int
    github_url: str
    github_repo_name: Optional[str]
    service_type: Optional[str]
    status: str
    current_step: int
    total_steps: int
    error_log: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeploymentStepResponse(BaseModel):
    """部署步骤响应"""
    id: int
    deployment_id: int
    step_number: int
    description: str
    command: Optional[str]
    status: str
    output: Optional[str]
    error_message: Optional[str]
    duration_ms: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class DeploymentWithStepsResponse(DeploymentResponse):
    """带步骤的部署响应"""
    steps: List[DeploymentStepResponse] = []


# =========== Helper Functions ===========

async def fetch_github_readme(github_url: str) -> str:
    """从 GitHub 获取 README 内容"""
    # 解析 GitHub URL
    # 格式：https://github.com/owner/repo
    parts = github_url.rstrip("/").split("/")
    if len(parts) < 5 or "github.com" not in parts[2]:
        raise ValueError(f"Invalid GitHub URL: {github_url}")

    owner = parts[3]
    repo = parts[4]

    # 尝试不同的 README 文件
    readme_paths = [
        f"README.md",
        f"readme.md",
        f"Readme.md",
        f"README.MD",
    ]

    async with aiohttp.ClientSession() as session:
        for path in readme_paths:
            # 尝试 main 分支
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{path}"
            try:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.text()
            except Exception:
                pass

            # 尝试 master 分支
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{path}"
            try:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.text()
            except Exception:
                pass

    raise ValueError(f"Could not fetch README from {github_url}")


def extract_repo_name(github_url: str) -> str:
    """从 GitHub URL 提取仓库名"""
    parts = github_url.rstrip("/").split("/")
    if len(parts) >= 5:
        return parts[4]
    return "unknown"


# =========== API Endpoints ===========

@router.post("/", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    deployment_data: DeploymentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    创建部署任务

    - **server_id**: 服务器 ID
    - **github_url**: GitHub 项目地址
    - **service_type**: 服务类型 (可选)
    """
    # 验证服务器存在
    server = db.query(Server).filter(
        Server.id == deployment_data.server_id,
        Server.user_id == current_user.id
    ).first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    # 创建部署记录
    deployment = Deployment(
        user_id=current_user.id,
        server_id=deployment_data.server_id,
        github_url=deployment_data.github_url,
        github_repo_name=extract_repo_name(deployment_data.github_url),
        service_type=deployment_data.service_type,
        status="pending",
        current_step=0,
        total_steps=0
    )

    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    # 在后台执行部署
    background_tasks.add_task(
        execute_deployment,
        deployment_id=deployment.id,
        db=db
    )

    logger.info(f"Deployment created: {deployment.id} for {deployment_data.github_url}")
    return deployment


async def execute_deployment(deployment_id: int, db):
    """后台执行部署任务"""
    from sqlalchemy.orm import Session

    # 重新获取 db session (background task 中需要新的 session)
    if not isinstance(db, Session):
        db = Session(db.bind)

    try:
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            logger.error(f"Deployment {deployment_id} not found")
            return

        server = db.query(Server).filter(Server.id == deployment.server_id).first()
        if not server:
            raise Exception(f"Server {deployment.server_id} not found")

        # 更新状态为 running
        deployment.status = "running"
        db.commit()

        # 发送 WebSocket 更新
        await websocket_manager.broadcast_deployment_update(deployment_id, {
            "status": "running",
            "current_step": 0,
            "total_steps": 0
        })

        logger.info(f"Starting deployment {deployment_id} for {deployment.github_url}")

        # 1. 获取 README 内容
        try:
            readme_content = await fetch_github_readme(deployment.github_url)
        except Exception as e:
            raise Exception(f"Failed to fetch README: {str(e)}")

        # 2. 生成部署计划
        provider_router = ProviderRouter()
        planner = DeployPlanner(provider_router)
        deploy_plan = await planner.generate_plan(
            github_url=deployment.github_url,
            readme_content=readme_content,
            os_type=server.os_type,
            os_version=server.os_version
        )

        # 更新部署的总步骤数
        deployment.total_steps = len(deploy_plan.steps)
        db.commit()

        # 发送 WebSocket 更新
        await websocket_manager.broadcast_deployment_update(deployment_id, {
            "status": "running",
            "current_step": 0,
            "total_steps": len(deploy_plan.steps)
        })

        # 保存部署步骤到数据库
        db_steps = []
        for step in deploy_plan.steps:
            db_step = DeploymentStep(
                deployment_id=deployment.id,
                step_number=step.number,
                description=step.description,
                command=step.command,
                status="pending"
            )
            db.add(db_step)
            db_steps.append(db_step)
        db.commit()

        # 3. 准备 SSH 连接
        credentials_json = encryptor.decrypt_base64(server.credentials)
        credentials_data = json.loads(credentials_json)

        ssh_creds = SSHCredentials(
            host=server.host,
            port=server.port,
            username=credentials_data.get("username", "root"),
            password=credentials_data.get("password"),
            ssh_key=credentials_data.get("ssh_key")
        )

        # 4. 执行部署
        async with SSHClient() as ssh_client:
            connected = await ssh_client.connect(ssh_creds)
            if not connected:
                raise Exception(f"Failed to connect to SSH server {server.host}:{server.port}")

            # 初始化 AI debugger 和 knowledge retriever
            ai_debugger = AIDebugger(provider_router)
            knowledge_retriever = KnowledgeRetriever(db)

            # 创建执行器
            executor = DeployExecutor(ssh_client, ai_debugger)

            # 执行计划
            async def on_step_complete(step):
                """每步完成后的回调"""
                # 更新数据库中的步骤状态
                db_step = db.query(DeploymentStep).filter(
                    DeploymentStep.deployment_id == deployment.id,
                    DeploymentStep.step_number == step.number
                ).first()
                if db_step:
                    db_step.status = step.status
                    db_step.output = step.output[:10000] if step.output else None
                    db_step.error_message = step.error_message[:10000] if step.error_message else None
                    db_step.duration_ms = step.duration_ms
                    db.commit()

                # 更新部署的当前步骤
                deployment.current_step = step.number
                db.commit()

                # 发送 WebSocket 日志
                await websocket_manager.broadcast_step_log(deployment_id, step.number, {
                    "step_number": step.number,
                    "description": step.description,
                    "command": step.command,
                    "status": step.status,
                    "output": step.output,
                    "error_message": step.error_message,
                    "duration_ms": step.duration_ms
                })

                logger.info(f"Step {step.number} completed: {step.status}")

            success = await executor.execute_plan(deploy_plan, on_step_complete)

            # 更新部署状态
            if success:
                deployment.status = "success"
                logger.info(f"Deployment {deployment_id} completed successfully")

                # 发送 WebSocket 完成通知
                await websocket_manager.broadcast_deployment_complete(deployment_id, True)

                # 存储成功案例到知识库
                deploy_steps_data = [
                    {"step": s.step_number, "description": s.description, "command": s.command, "output": s.output}
                    for s in db_steps
                ]
                await knowledge_retriever.store_case(
                    github_url=deployment.github_url,
                    os_type=server.os_type,
                    os_version=server.os_version,
                    service_type=deploy_plan.service_type or deployment.service_type or "web",
                    deploy_steps=deploy_steps_data,
                    common_errors=[],
                    success=True
                )
            else:
                deployment.status = "failed"
                deployment.error_log = f"Deployment failed at step {deployment.current_step}"
                logger.error(f"Deployment {deployment_id} failed")

                # 发送 WebSocket 失败通知
                await websocket_manager.broadcast_deployment_complete(
                    deployment_id,
                    False,
                    f"Failed at step {deployment.current_step}"
                )

                # 存储失败案例到知识库
                failed_step = deploy_plan.steps[deployment.current_step - 1] if deployment.current_step > 0 else None
                common_errors = []
                if failed_step and failed_step.error_message:
                    common_errors = [{"step": failed_step.number, "error": failed_step.error_message}]

                await knowledge_retriever.store_case(
                    github_url=deployment.github_url,
                    os_type=server.os_type,
                    os_version=server.os_version,
                    service_type=deploy_plan.service_type or deployment.service_type or "web",
                    deploy_steps=[
                        {"step": s.step_number, "description": s.description, "command": s.command, "output": s.output}
                        for s in deploy_plan.steps[:deployment.current_step]
                    ],
                    common_errors=common_errors,
                    success=False
                )

            db.commit()

    except Exception as e:
        logger.error(f"Deployment {deployment_id} error: {e}")
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if deployment:
            deployment.status = "failed"
            deployment.error_log = str(e)[:10000]
            db.commit()

        # 发送 WebSocket 错误通知
        try:
            await websocket_manager.broadcast_deployment_complete(deployment_id, False, str(e))
        except Exception:
            pass  # WebSocket 可能已经断开


@router.get("/", response_model=List[DeploymentResponse])
async def list_deployments(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """列出用户的部署历史"""
    query = db.query(Deployment).filter(Deployment.user_id == current_user.id)

    if status_filter:
        query = query.filter(Deployment.status == status_filter)

    deployments = query.order_by(Deployment.created_at.desc()).offset(skip).limit(limit).all()
    return deployments


@router.get("/{deployment_id}", response_model=DeploymentWithStepsResponse)
async def get_deployment(
    deployment_id: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """获取部署详情"""
    deployment = db.query(Deployment).filter(
        Deployment.id == deployment_id,
        Deployment.user_id == current_user.id
    ).first()

    if not deployment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    # 获取步骤
    steps = db.query(DeploymentStep).filter(
        DeploymentStep.deployment_id == deployment_id
    ).order_by(DeploymentStep.step_number).all()

    return DeploymentWithStepsResponse(
        id=deployment.id, user_id=deployment.user_id, server_id=deployment.server_id,
        github_url=deployment.github_url, github_repo_name=deployment.github_repo_name,
        service_type=deployment.service_type, status=deployment.status,
        current_step=deployment.current_step, total_steps=deployment.total_steps,
        error_log=deployment.error_log, created_at=deployment.created_at, updated_at=deployment.updated_at,
        steps=[
            DeploymentStepResponse(
                id=s.id, deployment_id=s.deployment_id, step_number=s.step_number,
                description=s.description, command=s.command, status=s.status,
                output=s.output, error_message=s.error_message, duration_ms=s.duration_ms,
                created_at=s.created_at
            ) for s in steps
        ]
    )


@router.post("/{deployment_id}/retry")
async def retry_deployment(
    deployment_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """重试失败的部署"""
    deployment = db.query(Deployment).filter(
        Deployment.id == deployment_id,
        Deployment.user_id == current_user.id
    ).first()

    if not deployment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    if deployment.status != "failed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only failed deployments can be retried")

    deployment.status = "pending"
    deployment.current_step = 0
    deployment.error_log = None
    db.commit()

    db.query(DeploymentStep).filter(DeploymentStep.deployment_id == deployment_id).update({"status": "pending"})
    db.commit()

    background_tasks.add_task(execute_deployment, deployment_id, db)
    return {"message": "Deployment retry scheduled"}


@router.post("/{deployment_id}/cancel")
async def cancel_deployment(
    deployment_id: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """取消进行中的部署"""
    deployment = db.query(Deployment).filter(
        Deployment.id == deployment_id,
        Deployment.user_id == current_user.id
    ).first()

    if not deployment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    if deployment.status != "running":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only running deployments can be cancelled")

    deployment.status = "cancelled"
    db.commit()
    return {"message": "Deployment cancelled"}


@router.websocket("/ws/{deployment_id}")
async def deployment_websocket(
    websocket: WebSocket,
    deployment_id: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    WebSocket 连接，实时接收部署日志

    前端连接后可以接收以下类型的消息:
    - deployment_update: 部署状态更新
    - step_log: 步骤执行日志
    - deployment_complete: 部署完成
    """
    # 验证部署属于当前用户
    deployment = db.query(Deployment).filter(
        Deployment.id == deployment_id,
        Deployment.user_id == current_user.id
    ).first()

    if not deployment:
        await websocket.close(code=4004, reason="Deployment not found")
        return

    # 连接 WebSocket
    await websocket_manager.connect(websocket, deployment_id)

    # 发送当前状态
    await websocket.send_json({
        "type": "deployment_update",
        "deployment_id": deployment_id,
        "data": {
            "status": deployment.status,
            "current_step": deployment.current_step,
            "total_steps": deployment.total_steps
        }
    })

    try:
        # 保持连接，等待消息
        while True:
            # 接收客户端消息 (心跳等)
            data = await websocket.receive_text()
            # 可以处理客户端消息，如 ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, deployment_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket, deployment_id)


# =========== AI Chat Endpoints ===========

class ChatMessage(BaseModel):
    """聊天消息"""
    message: str = Field(..., description="用户消息")
    context: Optional[Dict] = Field(None, description="额外上下文")


class ChatResponse(BaseModel):
    """聊天响应"""
    reply: str = Field(..., description="AI 回复")
    deployment_id: int = Field(..., description="部署 ID")


@router.post("/{deployment_id}/chat", response_model=ChatResponse)
async def chat_with_ai(
    deployment_id: int,
    chat_data: ChatMessage,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    与 AI 助手对话，获取排错建议

    - **message**: 用户消息
    - **context**: 额外上下文 (可选)
    """
    # 验证部署属于当前用户
    deployment = db.query(Deployment).filter(
        Deployment.id == deployment_id,
        Deployment.user_id == current_user.id
    ).first()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )

    # 获取部署步骤
    steps = db.query(DeploymentStep).filter(
        DeploymentStep.deployment_id == deployment_id
    ).order_by(DeploymentStep.step_number).all()

    # 获取服务器信息
    server = db.query(Server).filter(Server.id == deployment.server_id).first()

    # 找到失败的步骤
    failed_step = None
    previous_steps = []
    for step in steps:
        if step.status == "failed":
            failed_step = step
            break
        elif step.status in ["success", "running"]:
            previous_steps.append(step)

    # 初始化 AI debugger
    provider_router = ProviderRouter()
    ai_debugger = AIDebugger(provider_router)

    # 如果有失败的步骤，先进行分析
    if failed_step:
        # 构建失败步骤的上下文
        failed_step_context = type('obj', (object,), {
            'number': failed_step.step_number,
            'description': failed_step.description,
            'command': failed_step.command,
            'error_message': failed_step.error_message,
            'status': failed_step.status
        })

        previous_steps_context = [
            type('obj', (object,), {
                'number': s.step_number,
                'description': s.description,
                'command': s.command,
                'output': s.output,
                'status': s.status
            })
            for s in previous_steps
        ]

        # 分析错误
        debug_result = await ai_debugger.analyze(
            failed_step=failed_step_context,
            previous_steps=previous_steps_context,
            os_type=server.os_type if server else "ubuntu",
            os_version=server.os_version if server else "22.04",
            service_type=deployment.service_type or "web"
        )

        # 构建增强提示
        enhanced_message = f"""
用户问题：{chat_data.message}

AI 初步分析:
- 错误分析：{debug_result.analysis}
- 解决方案：{debug_result.solution}
- 建议命令：{debug_result.commands}
- 置信度：{debug_result.confidence * 100:.0f}%

请根据以上分析回答用户的问题。
"""
    else:
        enhanced_message = chat_data.message

    # 获取 AI 回复
    reply = await ai_debugger.chat(
        deployment_id=deployment_id,
        user_message=enhanced_message,
        context=chat_data.context
    )

    return ChatResponse(
        reply=reply,
        deployment_id=deployment_id
    )


@router.post("/{deployment_id}/chat/clear")
async def clear_chat_history(
    deployment_id: int,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """清除对话历史"""
    deployment = db.query(Deployment).filter(
        Deployment.id == deployment_id,
        Deployment.user_id == current_user.id
    ).first()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )

    provider_router = ProviderRouter()
    ai_debugger = AIDebugger(provider_router)
    ai_debugger.clear_conversation(deployment_id)

    return {"message": "Chat history cleared"}
