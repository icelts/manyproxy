#!/usr/bin/env python3
"""
调试session state接口
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal
from app.services.session_service import SessionService
from app.models.user import User

async def debug_session_state():
    """调试session state"""
    async with AsyncSessionLocal() as db:
        # 获取admin用户
        from sqlalchemy.future import select
        result = await db.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        
        if not user:
            print("Admin user not found")
            return
            
        print(f"Found user: {user.username}, id: {user.id}")
        
        try:
            # 测试build_session_envelope
            envelope = await SessionService.build_session_envelope(user, db=db)
            print("Session envelope built successfully:")
            print(f"  Token: {envelope.token[:20]}...")
            print(f"  API Key: {envelope.api_key}")
            print(f"  User: {envelope.user.username}")
            print(f"  Refreshed at: {envelope.refreshed_at}")
            
            # 测试序列化
            import json
            from datetime import datetime
            
            def datetime_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            
            data = envelope.model_dump()
            json_str = json.dumps(data, default=datetime_serializer)
            print("JSON serialization successful")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_session_state())
