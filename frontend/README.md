# SerPro 前端

基于 React + TypeScript + Vite 的前端应用

## 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite 5
- **样式**: TailwindCSS + shadcn/ui
- **状态管理**: Zustand
- **数据获取**: TanStack Query (React Query)
- **路由**: React Router v6
- **图表**: Recharts
- **图标**: Lucide React

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 项目结构

```
src/
├── components/
│   ├── ui/           # 基础 UI 组件
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── card.tsx
│   │   └── badge.tsx
│   └── layout/       # 布局组件
│       ├── AuthLayout.tsx
│       ├── DashboardLayout.tsx
│       └── SidebarNav.tsx
├── pages/
│   ├── auth/         # 认证页面
│   │   ├── Login.tsx
│   │   └── Register.tsx
│   ├── dashboard/    # Dashboard 页面
│   ├── servers/      # 服务器管理
│   ├── deployments/  # 部署历史
│   ├── knowledge/    # 知识库
│   ├── settings/     # 设置
│   └── admin/        # 管理员后台
├── lib/
│   ├── api.ts        # API 客户端
│   └── utils.ts      # 工具函数
├── store/
│   └── useAuthStore.ts  # 认证状态
├── types/
│   └── index.ts      # TypeScript 类型
├── App.tsx           # 应用入口
├── main.tsx          # React 入口
└── index.css         # 全局样式
```

## 功能模块

### 认证模块
- 用户登录
- 用户注册
- JWT Token 管理
- 自动刷新 Token

### 用户 Dashboard
- 概览统计
- 服务器管理
- 部署历史
- 知识库浏览
- 个人设置

### 管理员后台
- 用户管理 (禁用/启用/角色分配/重置密码)
- 系统配置
- 错误报表
- 系统监控

## API 集成

前端通过 Axios 与后端 API 通信，自动处理：
- 请求 Token 注入
- 401 自动刷新 Token
- 刷新失败自动登出

## 组件库

使用 shadcn/ui 组件库，基于 Radix UI 构建：

- Button - 按钮
- Input - 输入框
- Card - 卡片
- Badge - 徽章
- Dialog - 对话框
- Select - 选择器
- Tabs - 标签页
- Toast - 提示

## 状态管理

使用 Zustand 进行全局状态管理：
- 认证状态 (useAuthStore)
- 本地持久化

使用 TanStack Query 进行服务器状态管理：
- 自动缓存
- 自动重新验证
- 乐观更新

## 构建部署

### Docker 构建

```bash
docker build -f frontend/Dockerfile -t serapro-frontend .
```

### Nginx 配置

生产环境使用 Nginx 托管静态文件：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
