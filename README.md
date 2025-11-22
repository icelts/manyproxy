# ManyProxy - 代理管理系统

一个功能完整的代理管理系统，支持用户管理、代理服务、余额充值、订单管理等功能。

## 🚀 功能特性

### 核心功能
- **用户认证系统** - 注册、登录、JWT认证
- **代理管理** - 添加、编辑、删除、监控代理服务
- **余额系统** - 用户余额管理、充值功能
- **订单管理** - 订单创建、状态跟踪、历史记录
- **支付系统** - 加密货币支付支持（BTC、ETH、USDT等）
- **管理员面板** - 用户管理、系统监控、数据统计

### 技术特性
- **RESTful API** - 完整的API接口
- **实时监控** - 代理状态实时更新
- **响应式设计** - 支持移动端访问
- **数据库迁移** - Alembic版本控制
- **安全性** - 密码加密、JWT认证、权限控制

## 🛠 技术栈

### 后端
- **FastAPI** - 现代Python Web框架
- **SQLAlchemy** - ORM数据库操作
- **Alembic** - 数据库迁移工具
- **Pydantic** - 数据验证和序列化
- **JWT** - 身份认证
- **MySQL** - 数据库

### 前端
- **原生JavaScript** - 无框架依赖
- **HTML5/CSS3** - 现代Web标准
- **Bootstrap** - UI组件库
- **Font Awesome** - 图标库

### 支付集成
- **加密货币支付** - 支持多种主流加密货币
- **实时汇率** - 动态汇率更新
- **支付监控** - 自动确认支付状态

## 📦 安装部署

### 环境要求
- Python 3.8+
- pip 包管理器

### 快速开始

1. **克隆项目**
```bash
git clone <repository-url>
cd manyproxy
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置必要的环境变量
```

4. **运行应用**
```bash
# 使用启动脚本（推荐）
python run.py

# 或直接使用uvicorn
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **访问应用**
- 前端界面: http://localhost:8000/frontend/index.html
- API文档: http://localhost:8000/docs
- 管理界面: http://localhost:8000/frontend/pages/admin.html

### 默认账户
- **管理员**: admin / admin123
- **演示用户**: demo / demo123

> ⚠️ 安全提示：请在生产环境中修改默认密码

## 📁 项目结构

```
manyproxy/
├── app/                    # 后端应用
│   ├── api/               # API路由
│   │   └── v1/           # API版本1
│   │       ├── endpoints/ # 端点定义
│   │       └── api.py    # 路由汇总
│   ├── core/             # 核心配置
│   │   ├── config.py     # 应用配置
│   │   ├── database.py   # 数据库配置
│   │   └── security.py   # 安全相关
│   ├── models/           # 数据模型
│   │   ├── user.py       # 用户模型
│   │   ├── proxy.py      # 代理模型
│   │   └── order.py      # 订单模型
│   ├── schemas/          # Pydantic模式
│   │   ├── user.py       # 用户模式
│   │   ├── proxy.py      # 代理模式
│   │   └── order.py      # 订单模式
│   └── services/         # 业务逻辑
│       ├── auth_service.py    # 认证服务
│       ├── proxy_service.py   # 代理服务
│       ├── order_service.py   # 订单服务
│       └── crypto_payment.py  # 支付服务
├── frontend/             # 前端文件
│   ├── pages/           # 页面文件
│   │   ├── dashboard.html    # 仪表板
│   │   ├── proxy.html        # 代理管理
│   │   ├── orders.html       # 订单管理
│   │   ├── recharge.html     # 充值页面
│   │   └── admin.html        # 管理面板
│   ├── js/              # JavaScript文件
│   │   ├── app.js           # 主应用
│   │   ├── auth.js          # 认证模块
│   │   ├── proxy.js         # 代理模块
│   │   ├── orders.js        # 订单模块
│   │   └── admin.js         # 管理模块
│   └── css/             # 样式文件
│       └── style.css        # 主样式
├── alembic/              # 数据库迁移
│   └── versions/        # 迁移版本
├── run.py               # 启动脚本
├── requirements.txt     # 依赖列表
├── alembic.ini         # Alembic配置
└── .env.example        # 环境变量示例
```

## 🔧 开发指南

### 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### API开发

所有API端点都遵循RESTful规范，支持自动文档生成：

- **认证**: `/api/v1/session/`
- **代理**: `/api/v1/proxy/`
- **订单**: `/api/v1/orders/`
- **管理**: `/api/v1/admin/`

### 前端开发

前端采用模块化设计，每个页面对应独立的JavaScript文件：

- 使用原生JavaScript，无框架依赖
- 模块化的代码组织
- 响应式设计，支持移动端
- 统一的API调用接口

## 🔐 安全特性

- **密码加密**: 使用bcrypt加密存储
- **JWT认证**: 无状态身份验证
- **权限控制**: 基于角色的访问控制
- **CORS配置**: 跨域请求安全控制
- **输入验证**: Pydantic数据验证

## 💳 支付系统

### 支持的加密货币
- Bitcoin (BTC)
- Ethereum (ETH)
- Tether (USDT)
- USD Coin (USDC)

### 支付流程
1. 用户选择充值金额和加密货币
2. 系统生成支付地址和二维码
3. 用户转账到指定地址
4. 系统自动监控区块链确认
5. 确认后自动充值到用户余额

## 📊 管理功能

### 用户管理
- 查看所有用户列表
- 用户状态管理
- 余额调整
- 权限设置

### 系统监控
- 实时统计数据
- 订单状态监控
- 支付状态跟踪
- 系统日志查看

## 🚀 部署指南

### 开发环境
```bash
python run.py --reload
```

### 生产环境
```bash
# 使用Gunicorn部署
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# 或使用Docker
docker build -t manyproxy .
docker run -p 8000:8000 manyproxy
```

### 环境变量配置
```env
# 数据库配置
DATABASE_URL=mysql+aiomysql://username:password@localhost:3306/database_name

# JWT配置
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 支付配置
CRYPTO_PAYMENT_ENABLED=true
PAYMENT_CALLBACK_URL=http://localhost:8000/api/v1/orders/payments/callback
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🆘 支持

如果您遇到问题或有建议，请：

1. 查看 [API文档](http://localhost:8000/docs)
2. 检查 [Issues](../../issues)
3. 创建新的 Issue

## 🔄 更新日志

### v1.0.0 (2025-10-03)
- ✨ 初始版本发布
- 🔐 完整的用户认证系统
- 📊 代理管理功能
- 💰 余额充值系统
- 📱 响应式前端界面
- 🔧 管理员面板
- 💳 加密货币支付集成

---

**ManyProxy** - 让代理管理变得简单高效！
