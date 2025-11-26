#!/usr/bin/env python3
"""
检查用户密码
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.core.security import verify_password
from app.core.config import settings

async def check_users():
    """检查所有用户"""
    # 创建数据库连接
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        print(f"找到 {len(users)} 个用户:")
        
        for user in users:
            print(f"\n用户名: {user.username}")
            print(f"邮箱: {user.email}")
            print(f"余额: ${user.balance}")
            print(f"管理员: {user.is_admin}")
            print(f"激活: {user.is_active}")
            
            # 测试常见密码
            test_passwords = ["demo", "demo123", "admin", "password", "123456"]
            for pwd in test_passwords:
                if verify_password(pwd, user.password_hash):
                    print(f"✅ 正确密码: {pwd}")
                    break
            else:
                print("❌ 未找到匹配的密码")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_users())
