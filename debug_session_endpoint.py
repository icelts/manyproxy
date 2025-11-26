#!/usr/bin/env python3
"""
调试session state端点
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal
from app.core.security import verify_token
from app.services.session_service import SessionService
from app.models.user import User
from sqlalchemy.future import select

async def debug_session_endpoint():
    """调试session state端点"""
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImlzX2FkbWluIjp0cnVlLCJleHAiOjE3NjQxNzU1ODF9.9si15Prw8YxvsyWW3ZWa8pJeyzAmFl6S-vYFnroYEB0"
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. 测试token验证
            print("1. Testing token verification...")
            payload = verify_token(token)
            print(f"   Token payload: {payload}")
            
            # 2. 测试用户解析
            print("2. Testing user resolution from token...")
            user = await SessionService.resolve_user_from_token(db, token)
            if not user:
                print("   User not found!")
                return
            print(f"   Found user: {user.username}, id: {user.id}, active: {user.is_active}")
            
            # 3. 测试session envelope构建
            print("3. Testing session envelope building...")
            envelope = await SessionService.build_session_envelope(user, existing_token=token, db=db)
            print(f"   Envelope built successfully")
            print(f"   API Key: {envelope.api_key}")
            
            # 4. 测试完整的端点逻辑
            print("4. Testing complete endpoint logic...")
            from app.schemas.session import SessionEnvelope
            
            # 模拟FastAPI的响应模型验证
            response_data = SessionEnvelope(
                token=envelope.token,
                token_type=envelope.token_type,
                api_key=envelope.api_key,
                user=envelope.user,
                abilities=envelope.abilities,
                pages=envelope.pages,
                refreshed_at=envelope.refreshed_at
            )
            print("   Response model validation successful")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_session_endpoint())
