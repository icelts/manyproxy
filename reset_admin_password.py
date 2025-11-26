import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash

async def reset_admin_password():
    async with AsyncSessionLocal() as db:
        # 获取admin用户
        result = await db.execute(text("SELECT id, username FROM users WHERE username = 'admin'"))
        admin = result.fetchone()
        if admin:
            # 重新生成密码哈希
            new_hash = get_password_hash('admin123')
            await db.execute(text("UPDATE users SET password_hash = :hash WHERE username = 'admin'"), {"hash": new_hash})
            await db.commit()
            print('Admin密码已重置')
        else:
            print('Admin用户不存在')

if __name__ == "__main__":
    asyncio.run(reset_admin_password())
