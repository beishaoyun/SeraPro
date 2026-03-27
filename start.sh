#!/bin/bash
# SerPro 快速启动脚本

set -e

echo "=========================================="
echo "SerPro 启动脚本"
echo "=========================================="

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 检查环境配置
if [ ! -f .env ]; then
    echo "错误：.env 文件不存在"
    echo "请复制 .env.example 为 .env 并配置环境变量"
    exit 1
fi

# 启动数据库和 Redis (如果未运行)
echo ""
echo "检查 Docker 容器..."
docker-compose ps || {
    echo "启动 Docker 容器..."
    docker-compose up -d postgres redis
    sleep 5
}

# 运行数据库迁移
echo ""
echo "运行数据库迁移..."
alembic upgrade head

# 启动应用
echo ""
echo "启动 SerPro 应用..."
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
