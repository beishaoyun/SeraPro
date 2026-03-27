#!/bin/bash
# SerPro 安装脚本

set -e

echo "=========================================="
echo "SerPro 安装脚本"
echo "=========================================="

# 检查 Python 版本
echo ""
echo "检查 Python 版本..."
python3 --version || { echo "Python3 未安装，请先安装 Python 3.11+"; exit 1; }

# 创建虚拟环境（可选）
read -p "是否创建 Python 虚拟环境？(y/n) " create_venv
if [ "$create_venv" = "y" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
fi

# 安装依赖
echo ""
echo "安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 创建日志目录
echo ""
echo "创建日志目录..."
mkdir -p logs

# 复制环境配置
if [ ! -f .env ]; then
    echo ""
    echo "创建环境配置文件..."
    cp .env.example .env
    echo "请编辑 .env 文件配置数据库和 AI Provider"
fi

# 安装完成
echo ""
echo "=========================================="
echo "安装完成!"
echo "=========================================="
echo ""
echo "下一步:"
echo "1. 编辑 .env 文件配置环境变量"
echo "2. 启动数据库：docker-compose up -d postgres redis"
echo "3. 运行数据库迁移：alembic upgrade head"
echo "4. 启动服务：uvicorn src.api.main:app --reload"
echo ""
