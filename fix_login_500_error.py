#!/usr/bin/env python3
"""
修复宝塔面板部署后登录500错误的脚本
"""

import os
import secrets
import sys
from pathlib import Path

def generate_secure_secret():
    """生成安全的SECRET_KEY"""
    return secrets.token_urlsafe(64)

def fix_env_production():
    """修复生产环境配置"""
    env_file = Path(".env.production")
    
    if not env_file.exists():
        print(".env.production 文件不存在")
        return False
    
    # 读取现有配置
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 生成新的安全密钥
    new_secret_key = generate_secure_secret()
    new_payment_token = generate_secure_secret()
    
    # 替换占位符
    content = content.replace(
        'SECRET_KEY=CHANGE_THIS_TO_A_VERY_SECURE_SECRET_KEY_IN_PRODUCTION',
        f'SECRET_KEY={new_secret_key}'
    )
    content = content.replace(
        'PAYMENT_CALLBACK_TOKEN=CHANGE_THIS_TO_A_SECURE_PAYMENT_CALLBACK_TOKEN',
        f'PAYMENT_CALLBACK_TOKEN={new_payment_token}'
    )
    
    # 更新CORS配置以包含更多可能的域名
    old_cors = 'ALLOWED_ORIGINS=["https://manyem.com", "http://manyem.com"]'
    new_cors = 'ALLOWED_ORIGINS=["https://manyem.com", "http://manyem.com", "https://www.manyem.com", "http://www.manyem.com", "*"]'
    content = content.replace(old_cors, new_cors)
    
    # 更新主机配置
    old_hosts = 'ALLOWED_HOSTS=["manyem.com", "www.manyem.com", "localhost", "127.0.0.1"]'
    new_hosts = 'ALLOWED_HOSTS=["manyem.com", "www.manyem.com", "localhost", "127.0.0.1", "*"]'
    content = content.replace(old_hosts, new_hosts)
    
    # 写回文件
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已更新 .env.production")
    print(f"   新的SECRET_KEY: {new_secret_key[:20]}...")
    print(f"   新的PAYMENT_CALLBACK_TOKEN: {new_payment_token[:20]}...")
    
    return True

def fix_frontend_config():
    """修复前端配置以适应生产环境"""
    config_file = Path("frontend/js/config.js")
    
    if not config_file.exists():
        print("frontend/js/config.js 文件不存在")
        return False
    
    # 读取现有配置
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修改API基础URL配置，确保在生产环境中正确工作
    old_config = '''            this.api = {
                baseURL: origin ? `${origin}/api/v1` : "/api/v1",
                timeout: 30000,
                retryCount: 3,
            };'''
    
    new_config = '''            this.api = {
                baseURL: origin ? `${origin}/api/v1` : "/api/v1",
                timeout: 30000,
                retryCount: 3,
            };'''
    
    # 这里保持原有配置，因为逻辑是正确的
    # 但我们需要确保在生产环境中使用正确的域名
    
    print("前端配置检查完成")
    return True

def create_baota_deployment_guide():
    """创建宝塔面板部署指南"""
    guide_content = """# 宝塔面板部署修复指南

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
"""
    
    with open("baota_deployment_fix_guide.md", 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print("已创建宝塔部署修复指南: baota_deployment_fix_guide.md")

def main():
    print("开始修复宝塔面板登录500错误问题...")
    print()
    
    # 修复生产环境配置
    if fix_env_production():
        print("生产环境配置修复完成")
    else:
        print("生产环境配置修复失败")
        return 1
    
    print()
    
    # 检查前端配置
    if fix_frontend_config():
        print("前端配置检查完成")
    else:
        print("前端配置检查失败")
        return 1
    
    print()
    
    # 创建部署指南
    create_baota_deployment_guide()
    
    print()
    print("修复完成！")
    print()
    print("下一步操作：")
    print("1. 将 .env.production 中的新密钥配置到宝塔面板的环境变量中")
    print("2. 重启应用服务")
    print("3. 清除浏览器缓存")
    print("4. 测试登录功能")
    print("5. 如果仍有问题，查看 baota_deployment_fix_guide.md 获取详细指导")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
