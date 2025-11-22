import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal
from app.services.session_service import SessionService
from app.schemas.user import UserCreate

async def test_register():
    """测试用户注册功能"""
    print("开始测试用户注册...")
    
    # 创建测试数据
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )
    
    try:
        async with AsyncSessionLocal() as db:
            # 尝试创建用户
            user = await SessionService.register_user(db, user_data)
            print(f"用户创建成功: {user}")
            print(f"用户ID: {user.id}")
            print(f"用户名: {user.username}")
            print(f"邮箱: {user.email}")
            print(f"创建时间: {user.created_at}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_register())
