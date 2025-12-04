# ManyProxy 8000端口运行指南

## 项目概述

ManyProxy是一个基于FastAPI的代理IP管理平台，前后端服务统一运行在8000端口上。

## 服务架构

- **后端**: FastAPI应用，提供API服务和静态文件服务
- **前端**: HTML/CSS/JavaScript静态文件，通过FastAPI的StaticFiles中间件提供服务
- **数据库**: MySQL (通过aiomysql连接)
- **缓存**: Redis (可选，如果不可用会自动禁用)

## 启动方式

### 1. 初始化数据库（首次运行）
```bash
python run.py --init-db
```

### 2. 启动服务
```bash
python run.py
```

### 3. 开发模式启动（支持热重载）
```bash
python run.py --reload
```

### 4. 自定义配置
```bash
python run.py --host 0.0.0.0 --port 8000 --reload
```

## 访问地址

### 主要页面
- **首页**: http://localhost:8000/
- **前端入口**: http://localhost:8000/frontend/index.html
- **API文档**: http://localhost:8000/api/v1/docs
- **公共API文档**: http://localhost:8000/public/docs

### API端点
- **健康检查**: http://localhost:8000/health
- **API基础路径**: http://localhost:8000/api/v1/
- **公共API**: http://localhost:8000/public/

## 默认账户

系统会自动创建以下默认账户：

### 管理员账户
- **用户名**: admin
- **密码**: admin123
- **权限**: 管理员

### 演示账户
- **用户名**: demo
- **密码**: demo123
- **权限**: 普通用户

> ⚠️ **安全提醒**: 生产环境中请立即修改默认密码！

## 技术栈

- **后端框架**: FastAPI + Uvicorn
- **数据库ORM**: SQLAlchemy + Alembic
- **前端**: 原生HTML/CSS/JavaScript
- **认证**: API Key认证
- **日志**: Python logging + 文件轮转

## 项目结构

```
manyproxy/
├── app/                    # 后端应用
│   ├── api/               # API路由
│   ├── core/              # 核心配置
│   ├── models/            # 数据模型
│   ├── services/          # 业务逻辑
│   └── utils/             # 工具函数
├── frontend/              # 前端文件
│   ├── css/               # 样式文件
│   ├── js/                # JavaScript文件
│   ├── pages/             # 页面文件
│   └── components/        # 组件文件
├── alembic/               # 数据库迁移
├── logs/                  # 日志文件
└── run.py                 # 启动脚本
```

## 配置说明

主要配置文件：
- `app/core/config.py`: 应用配置
- `.env`: 环境变量配置
- `alembic.ini`: 数据库迁移配置

## 开发提示

1. **端口配置**: 服务默认运行在8000端口，可通过命令行参数修改
2. **静态文件**: 前端文件通过FastAPI的StaticFiles中间件提供服务
3. **热重载**: 开发时使用`--reload`参数启用代码热重载
4. **日志文件**: 应用日志保存在`logs/app.log`，支持自动轮转

## 故障排除

1. **Redis连接失败**: 如果Redis不可用，缓存功能会被禁用，不影响核心功能
2. **数据库连接**: 确保MySQL服务运行且连接配置正确
3. **端口占用**: 如果8000端口被占用，可使用`--port`参数指定其他端口

## 生产部署建议

1. 使用反向代理（如Nginx）
2. 启用HTTPS
3. 配置环境变量
4. 设置生产级日志
5. 修改默认密码
6. 限制允许的主机和来源
