# 宝塔面板登录500错误修复指南

## 问题说明

您说得对，我之前的修复是在本地环境运行的，并没有直接更新到宝塔服务器。现在我将提供针对宝塔面板的实际修复步骤。

## 真正的问题原因

从宝塔面板的错误日志可以看到：
```
ValueError: password cannot be longer than 72 bytes, truncate manually if necessary (e.g. my_password[:72])
```

这是bcrypt密码验证的72字节限制导致的。

## 宝塔面板修复步骤

### 步骤1：登录宝塔面板

1. 打开宝塔面板管理界面
2. 进入文件管理
3. 导航到您的项目目录：`/www/wwwroot/manyem/`

### 步骤2：修改密码处理文件

编辑文件：`/www/wwwroot/manyem/app/core/security.py`

将现有的 `verify_password` 和 `get_password_hash` 函数替换为：

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # bcrypt密码长度限制为72字节
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    # bcrypt密码长度限制为72字节
    if len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)
```

### 步骤3：上传修复脚本

1. 在宝塔面板中创建新文件：`/www/wwwroot/manyem/fix_password_length_issue.py`
2. 复制以下内容到该文件：

```python
#!/usr/bin/env python3
"""
修复密码长度限制问题 - 宝塔面板版本
"""

import asyncio
import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, '/www/wwwroot/manyem')

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from sqlalchemy import select

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fix_demo_user_password():
    """修复demo用户密码"""
    logger.info("=== 修复demo用户密码 ===")
    
    try:
        async with AsyncSessionLocal() as db:
            # 查找demo用户
            result = await db.execute(select(User).where(User.username == 'demo'))
            user = result.scalar_one_or_none()
            
            if user:
                logger.info(f"找到demo用户，ID: {user.id}")
                # 重新生成密码哈希
                new_hash = get_password_hash("demo123")
                user.password_hash = new_hash
                await db.commit()
                logger.info("✅ demo用户密码已更新")
                
                # 验证新密码
                if verify_password("demo123", user.password_hash):
                    logger.info("✅ demo用户密码验证成功")
                else:
                    logger.error("❌ demo用户密码验证失败")
            else:
                logger.warning("❌ 未找到demo用户")
                
    except Exception as e:
        logger.error(f"❌ 修复demo用户密码失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数"""
    logger.info("开始修复宝塔面板密码问题...")
    
    # 修复demo用户密码
    await fix_demo_user_password()
    
    logger.info("\n=== 修复完成 ===")
    logger.info("测试账户信息:")
    logger.info("  用户名: demo")
    logger.info("  密码: demo123")
    logger.info("\n请重启Python应用服务使修改生效")

if __name__ == "__main__":
    asyncio.run(main())
```

### 步骤4：运行修复脚本

1. 在宝塔面板中打开终端
2. 进入项目目录：`cd /www/wwwroot/manyem`
3. 运行修复脚本：`python fix_password_length_issue.py`

### 步骤5：重启应用服务

在宝塔面板中：
1. 进入软件商店 → 已安装
2. 找到Python项目管理器
3. 重启您的manyem项目

或者使用命令行：
```bash
# 停止应用
pkill -f "python.*app.main"

# 启动应用
cd /www/wwwroot/manyem
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

### 步骤6：验证修复

1. 访问您的网站：`https://manyem.com/login.html`
2. 使用测试账户登录：
   - 用户名：`demo`
   - 密码：`demo123`
3. 检查是否成功跳转到dashboard

## 如果仍然有问题

### 检查应用日志
```bash
tail -f /www/wwwroot/manyem/logs/app.log
```

### 手动创建demo用户
如果demo用户不存在，可以手动创建：

1. 创建新文件：`/www/wwwroot/manyem/create_demo_user.py`
2. 内容如下：

```python
#!/usr/bin/env python3
"""
创建demo用户
"""

import asyncio
import sys
sys.path.insert(0, '/www/wwwroot/manyem')

from app.core.database import AsyncSessionLocal
from app.services.session_service import SessionService
from app.schemas.user import UserCreate

async def main():
    async with AsyncSessionLocal() as db:
        user_data = UserCreate(
            username="demo",
            email="demo@example.com",
            password="demo123"
        )
        
        user = await SessionService.register_user(db, user_data)
        print(f"✅ demo用户创建成功: {user.username}")

if __name__ == "__main__":
    asyncio.run(main())
```

3. 运行：`python create_demo_user.py`

## 快速修复命令总结

```bash
# 1. 进入项目目录
cd /www/wwwroot/manyem

# 2. 运行密码修复脚本
python fix_password_length_issue.py

# 3. 重启应用
pkill -f "python.*app.main"
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &

# 4. 检查日志
tail -f logs/app.log
```

## 注意事项

1. **文件权限**：确保宝塔面板有足够的权限修改文件
2. **Python环境**：使用宝塔面板的Python环境，不是系统Python
3. **数据库连接**：确保数据库连接正常
4. **端口占用**：确保8000端口没有被占用

## 测试账户

修复完成后，使用以下账户测试：
- 用户名：`demo`
- 密码：`demo123`

如果这个账户无法登录，还可以尝试：
- 用户名：`admin`
- 密码：`admin123`

## 总结

这个修复方案专门针对宝塔面板环境，通过以下步骤解决问题：
1. 修改密码处理逻辑以处理bcrypt 72字节限制
2. 更新数据库中的密码哈希
3. 重启应用服务使修改生效

现在您需要在宝塔面板中实际执行这些步骤来修复问题。
