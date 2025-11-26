#!/usr/bin/env python3
"""
直接测试session state端点逻辑
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal
from app.api.v1.endpoints.session import get_current_active_user, session_state
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

async def debug_direct_session():
    """直接测试session state端点"""
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImlzX2FkbWluIjp0cnVlLCJleHAiOjE3NjQxNzU2OTl9.nPw-Pnnu_-l90e4Vp2CzfCWu86qTYU5camQe-SMYlGs"
    
    async with AsyncSessionLocal() as db:
        try:
            print("1. Testing get_current_active_user...")
            
            # 创建credentials对象
            security = HTTPBearer()
            credentials = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)
            
            # 调用get_current_active_user
            user = await get_current_active_user(db, credentials)
            print(f"   User found: {user.username}")
            
            print("2. Testing session_state endpoint...")
            
            # 调用session_state端点
            result = await session_state(user, db)
            print(f"   Session state result: {result}")
            print(f"   API Key: {result.api_key}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_direct_session())
