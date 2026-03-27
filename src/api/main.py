"""
SerPro API - 服务器自动化托管平台
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from src.core.credentials.encryption import CredentialEncryptor
from src.db.models import Base
from src.db.database import engine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Starting SerPro API...")

    # 初始化数据库
    # Base.metadata.create_all(bind=engine)

    yield

    # 关闭时执行
    logger.info("Shutting down SerPro API...")


# 创建 FastAPI 应用
app = FastAPI(
    title="SerPro API",
    description="服务器自动化托管平台",
    version="0.1.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "SerPro API",
        "version": "0.1.0",
        "description": "服务器自动化托管平台"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# 导入路由
from src.api.routes import auth, servers, deployments, knowledge, admin
from src.config import settings

# API 路由注册
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(servers.router, prefix="/api/v1/servers", tags=["服务器管理"])
app.include_router(deployments.router, prefix="/api/v1/deployments", tags=["部署管理"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["知识库"])
app.include_router(admin.users.router, prefix="/api/v1/admin/users", tags=["管理员 - 用户管理"])
app.include_router(admin.system.router, prefix="/api/v1/admin/system", tags=["管理员 - 系统配置"])
app.include_router(admin.error_reports.router, prefix="/api/v1/admin/errors", tags=["管理员 - 错误报表"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
