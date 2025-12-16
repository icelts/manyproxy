#!/usr/bin/env python3
"""
检查用户API密钥
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.user import User, APIKey
from app.core.config import settings

async def check_api_keys():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        # 检查所有用户
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        print("=== 用户列表 ===")
        for user in users:
            print(f'User: {user.username} (ID: {user.id}, Active: {user.is_active})')
        
        print("\n=== API密钥列表 ===")
        # 检查所有API密钥
        api_keys_result = await session.execute(select(APIKey))
        api_keys = api_keys_result.scalars().all()
        
        if not api_keys:
            print("没有找到任何API密钥")
        else:
            for api_key in api_keys:
                print(f'API Key: {api_key.api_key}')
                print(f'  User ID: {api_key.user_id}')
                print(f'  Name: {api_key.name}')
                print(f'  Active: {api_key.is_active}')
                print(f'  Created: {api_key.created_at}')
                print(f'  Last Used: {api_key.last_used_at}')
                print('---')

if __name__ == "__main__":
    asyncio.run(check_api_keys())
