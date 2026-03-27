# SerPro 部署清单

## 部署前检查

### 环境准备

- [ ] Python 3.11+ 已安装
- [ ] Docker 和 Docker Compose 已安装
- [ ] PostgreSQL 15+ 可访问
- [ ] Redis 7+ 可访问

### 配置文件

- [ ] `.env` 文件已创建并配置
  - [ ] `DATABASE_URL` 正确配置
  - [ ] `REDIS_URL` 正确配置
  - [ ] `SECRET_KEY` 已更改为随机值
  - [ ] `MASTER_KEY` 保持 32 字节
  - [ ] AI Provider API Key 已配置

### 数据库

- [ ] 数据库已创建
- [ ] 数据库迁移已运行 (`alembic upgrade head`)
- [ ] 数据库连接测试成功

### 依赖安装

```bash
# 使用安装脚本
./install.sh

# 或手动安装
pip install -r requirements.txt
```

## 本地开发部署

### 方式一：直接运行

```bash
# 启动数据库和 Redis
docker-compose up -d postgres redis

# 运行数据库迁移
alembic upgrade head

# 启动应用
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 方式二：使用启动脚本

```bash
./start.sh
```

### 验证

- [ ] 访问 http://localhost:8000/docs
- [ ] API 文档正常显示
- [ ] 健康检查端点返回 healthy：`/health`

## Docker 部署

### 开发环境

```bash
docker-compose up -d
```

### 生产环境

```bash
# 使用 nginx 反向代理
docker-compose --profile production up -d
```

### 验证

```bash
# 查看容器状态
docker-compose ps

# 查看应用日志
docker-compose logs -f app

# 查看数据库日志
docker-compose logs -f postgres
```

## 生产环境部署

### 1. 服务器准备

```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | bash

# 安装 Docker Compose
apt install docker-compose -y
```

### 2. 代码部署

```bash
# 克隆代码
git clone <repo-url> /opt/serapro
cd /opt/serapro

# 配置环境变量
cp .env.example .env
vim .env  # 编辑配置
```

### 3. SSL 证书配置

```bash
# 使用 Let's Encrypt
apt install certbot -y
certbot certonly --standalone -d your-domain.com
```

### 4. 启动服务

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose --profile production up -d
```

### 5. 配置防火墙

```bash
# 只开放必要端口
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 22/tcp    # SSH (限制 IP)
ufw enable
```

## 监控配置

### Prometheus 监控

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'serapro'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
```

### Grafana 告警

- CPU 使用率 > 80%
- 内存使用率 > 80%
- 错误率 > 5%
- 响应时间 P95 > 500ms

### 日志聚合

```bash
# 使用 ELK Stack
docker-compose up -d elasticsearch logstash kibana
```

## 备份策略

### 数据库备份

```bash
# 每日备份
pg_dump -U serapro serapro > /backup/serapro_$(date +%Y%m%d).sql

# 保留 30 天
find /backup -name "serapro_*.sql" -mtime +30 -delete
```

### 配置文件备份

```bash
tar -czf /backup/serapro_config_$(date +%Y%m%d).tar.gz .env nginx/
```

## 故障排查

### 应用无法启动

```bash
# 查看日志
docker-compose logs app

# 检查端口
netstat -tlnp | grep 8000

# 重启服务
docker-compose restart app
```

### 数据库连接失败

```bash
# 检查数据库状态
docker-compose ps postgres

# 测试连接
psql -h localhost -U serapro -d serapro

# 查看数据库日志
docker-compose logs postgres
```

### Redis 连接失败

```bash
# 检查 Redis 状态
docker-compose ps redis

# 测试连接
redis-cli ping

# 查看 Redis 日志
docker-compose logs redis
```

## 性能调优

### 数据库优化

```sql
-- 添加索引
CREATE INDEX idx_deployments_user_id ON deployments(user_id);
CREATE INDEX idx_deployments_status ON deployments(status);

-- 分析表
ANALYZE;
```

### 应用优化

```ini
# .env 配置
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

### Nginx 优化

```nginx
# 增加 worker 进程
worker_processes auto;

# 调整连接数
events {
    worker_connections 4096;
}
```

## 回滚流程

### 应用回滚

```bash
# 停止当前版本
docker-compose stop app

# 启动旧版本
docker run -d --name serapro-old <old-image-tag>

# 恢复数据库
psql -U serapro serapro < /backup/serapro_YYYYMMDD.sql
```

## 联系支持

- 项目文档：`README.md`
- 开发总结：`DEVELOPMENT_COMPLETE.md`
- 设计文档：`~/.gstack/projects/serapro/root-20260327-104725-eng-review.md`
