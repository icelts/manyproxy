#!/usr/bin/env python3
"""
创建测试用的API Key
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_async_session
from app.models.user import User
from app.models.proxy import APIKey
from app.core.security import generate_api_key
import uuid

async def create_test_api_key():
    """创建测试API Key"""
    async with get_async_session() as db:
        # 查找或创建测试用户
        result = await db.execute(
            "SELECT id FROM users WHERE username = 'testuser'"
        )
        user = result.fetchone()
        
        if not user:
            # 创建测试用户
            from app.core.security import get_password_hash
            test_user = User(
                username="testuser",
                email="test@example.com",
                hashed_password=get_password_hash("testpass123"),
                balance=1000.0,
                is_active=True
            )
            db.add(test_user)
            await db.flush()
            user_id = test_user.id
            print(f"✅ 创建测试用户: testuser")
        else:
            user_id = user[0]
            print(f"✅ 使用现有用户: testuser (ID: {user_id})")
        
        # 创建API Key
        api_key = generate_api_key()
        api_key_record = APIKey(
            user_id=user_id,
            api_key=api_key,
            name="Test API Key",
            is_active=True
        )
        db.add(api_key_record)
        await db.commit()
        
        print(f"✅ 创建API Key: {api_key}")
        print(f"📝 请将此API Key复制到测试脚本中使用")
        
        return api_key

if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 运行创建
    try:
        api_key = asyncio.run(create_test_api_key())
        print(f"\n🔑 测试API Key: {api_key}")
    except Exception as e:
        print(f"❌ 创建API Key失败: {e}")
