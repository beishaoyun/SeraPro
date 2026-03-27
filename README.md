# SerPro - 服务器自动化托管平台

## 项目简介

SerPro 是一个智能化的服务器托管平台，支持：

- **自动部署**：输入 GitHub 项目地址，AI 自动解析 README 生成部署计划
- **多 AI 平台**：支持 OpenAI、火山引擎豆包、阿里云通义千问、DeepSeek
- **智能排错**：部署失败时 AI 自动分析错误并提供修复方案
- **知识库**：自动记录成功/失败案例，支持 RAG 检索
- **多教程来源**：支持 GitHub、百度经验、CSDN、官方文档
- **管理员后台**：用户管理、系统配置、错误报表、日志监控

## 技术栈

- **后端**: FastAPI + Python 3.11
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7
- **AI**: LangChain + 多 LLM Provider
- **SSH**: Paramiko
- **加密**: AES-256-GCM + PBKDF2

## 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (可选)

### 本地开发

1. **克隆项目**
```bash
git clone <repo-url>
cd SerPro
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库和 AI Provider
```

4. **启动数据库和 Redis**
```bash
docker-compose up -d postgres redis
```

5. **运行数据库迁移**
```bash
alembic upgrade head
```

6. **启动开发服务器**
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

7. **访问 API 文档**
```
http://localhost:8000/docs
```

### Docker 部署

```bash
docker-compose up -d
```

## API 使用示例

### 1. 用户注册
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

### 2. 用户登录
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

### 3. 添加服务器
```bash
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "Production Server",
    "host": "192.168.1.100",
    "os_type": "ubuntu",
    "os_version": "22.04"
  }'
```

### 4. 创建部署
```bash
curl -X POST http://localhost:8000/api/v1/deployments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "server_id": 1,
    "github_url": "https://github.com/example/my-app"
  }'
```

## 项目结构

```
SerPro/
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI 应用入口
│   │   └── routes/          # API 路由
│   │       ├── auth.py      # 认证
│   │       ├── servers.py   # 服务器管理
│   │       ├── deployments.py  # 部署管理
│   │       ├── knowledge.py    # 知识库
│   │       └── admin/       # 管理员后台
│   ├── core/
│   │   ├── ai/              # AI 模块
│   │   │   ├── providers/   # 多 AI Provider
│   │   │   ├── debugger.py  # AI 排错
│   │   │   └── config.py    # AI 配置
│   │   ├── credentials/     # 凭证加密
│   │   ├── deployment/      # 部署引擎
│   │   │   ├── executor.py  # 执行器
│   │   │   └── planner.py   # 计划生成
│   │   ├── knowledge/       # 知识库
│   │   │   └── retriever.py # 检索器
│   │   ├── ssh/             # SSH 客户端
│   │   ├── errors/          # 错误处理
│   │   ├── notifications/   # 通知系统
│   │   └── tutorial/        # 教程解析
│   ├── db/
│   │   ├── database.py      # 数据库连接
│   │   └── models/          # 数据模型
│   └── config.py            # 应用配置
├── tests/                   # 测试用例
├── alembic/                 # 数据库迁移
├── docker-compose.yml       # Docker 编排
├── Dockerfile              # Docker 镜像
└── requirements.txt        # Python 依赖
```

## 多 AI Provider 配置

在 `.env` 文件中配置：

```ini
# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4

# 火山引擎豆包
VOLCENGINE_API_KEY=xxx
VOLCENGINE_MODEL=

# 阿里云通义千问
ALIBABA_API_KEY=xxx
ALIBABA_MODEL=

# DeepSeek
DEEPSEEK_API_KEY=xxx
DEEPSEEK_MODEL=

# Provider 选择：auto, openai, volcengine, alibaba, deepseek
AI_PROVIDER=auto
```

## 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_auth.py -v

# 生成覆盖率报告
pytest --cov=src/ --cov-report=html
```

## 监控与告警

### 错误通知渠道

- 邮件通知 (SMTP)
- 短信通知 (阿里云)
- 钉钉机器人
- 站内消息

### 配置通知

```ini
# 邮件
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=xxx

# 钉钉
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=xxx
```

## 开发指南

### 添加新的 AI Provider

1. 在 `src/core/ai/providers/` 创建新的 Provider 类
2. 继承 `BaseLLMProvider` 抽象基类
3. 实现 `chat_completion` 和 `get_model_price` 方法
4. 在 `ProviderRouter` 中注册

### 添加新的教程解析器

1. 在 `src/core/tutorial/parsers/` 创建解析器
2. 继承 `BaseTutorialParser`
3. 实现 `parse()` 方法
4. 在 `TutorialParser` 路由中注册

## 安全考虑

- **凭证加密**: AES-256-GCM 加密存储 SSH 凭证
- **密码哈希**: bcrypt 哈希用户密码
- **JWT 认证**: 基于 JWT 的无状态认证
- **审计日志**: 所有敏感操作记录审计日志
- **RBAC**: 基于角色的访问控制

## 许可证

MIT License
