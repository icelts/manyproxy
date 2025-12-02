# 宝塔面板部署修复指南

## 问题说明
登录时返回500错误通常是由于以下原因：

1. **环境变量配置不正确**
2. **CORS配置问题**
3. **数据库连接问题**
4. **Redis连接问题**

## 修复步骤

### 1. 环境变量配置
确保在宝塔面板中设置正确的环境变量：

```bash
# 在宝塔面板 -> 网站设置 -> 环境变量 中添加：
DATABASE_URL=mysql+aiomysql://manyem:WDfAsRpWeKsE6MCB@125.212.244.39:3306/manyem?charset=utf8mb4
DEBUG=false
ALLOW_DB_CREATE_ALL=false
SECRET_KEY=your_secure_secret_key_here
PAYMENT_CALLBACK_TOKEN=your_payment_token_here
REDIS_URL=redis://localhost:6379
ALLOWED_ORIGINS=["https://manyem.com", "http://manyem.com", "https://www.manyem.com", "http://www.manyem.com"]
ALLOWED_HOSTS=["manyem.com", "www.manyem.com", "localhost", "127.0.0.1"]
TOPPROXY_KEY=AcPHxnLQlmwzMbfoYKMifO
```

### 2. 数据库配置
确保MySQL数据库可以正常连接：
- 检查数据库用户权限
- 确认数据库表已创建
- 运行数据库迁移：`alembic upgrade head`

### 3. Redis配置
如果Redis不可用，应用会继续运行但缓存功能会被禁用。这是正常的。

### 4. 启动应用
使用以下命令启动应用：

```bash
# 设置环境变量
export $(cat .env.production | xargs)

# 启动应用
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Nginx配置
在宝塔面板中配置Nginx反向代理：

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## 测试步骤

1. 重启应用服务
2. 清除浏览器缓存
3. 尝试登录测试账户
4. 检查应用日志：`tail -f logs/app.log`

## 常见问题

### Q: 仍然出现500错误
A: 检查应用日志，通常会有详细的错误信息。

### Q: 数据库连接失败
A: 确认数据库地址、端口、用户名、密码正确。

### Q: CORS错误
A: 确保ALLOWED_ORIGINS包含访问的域名。

## 联系支持
如果问题仍然存在，请提供：
1. 完整的错误日志
2. 宝塔面板配置截图
3. 浏览器控制台错误信息
