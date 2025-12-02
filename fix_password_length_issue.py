#!/usr/bin/env python3
"""
修复密码长度限制问题
检查并修复数据库中可能存在的密码哈希问题
"""

import asyncio
import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

async def check_and_fix_passwords():
    """检查并修复密码问题"""
    logger.info("=== 检查和修复密码问题 ===")
    
    try:
        async with AsyncSessionLocal() as db:
            # 获取所有用户
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            for user in users:
                logger.info(f"检查用户: {user.username}")
                
                # 测试密码验证
                test_passwords = ["demo123", "admin123", "password", "123456"]
                
                for test_pwd in test_passwords:
                    try:
                        if verify_password(test_pwd, user.password_hash):
                            logger.info(f"✅ 用户 {user.username} 密码验证成功: {test_pwd}")
                            break
                    except Exception as e:
                        logger.warning(f"⚠️ 用户 {user.username} 密码验证失败: {e}")
                        
                        # 如果验证失败，尝试重新生成密码哈希
                        if "password cannot be longer than 72 bytes" in str(e):
                            logger.info(f"为用户 {user.username} 重新生成密码哈希...")
                            new_hash = get_password_hash(test_pwd)
                            user.password_hash = new_hash
                            await db.commit()
                            logger.info(f"✅ 用户 {user.username} 密码哈希已更新")
                            
                            # 验证新密码
                            if verify_password(test_pwd, user.password_hash):
                                logger.info(f"✅ 用户 {user.username} 新密码验证成功")
                            break
                else:
                    logger.warning(f"❌ 用户 {user.username} 所有测试密码都失败")
                    
    except Exception as e:
        logger.error(f"❌ 修复密码失败: {e}")
        import traceback
        traceback.print_exc()

async def create_demo_user():
    """创建演示用户"""
    logger.info("=== 创建演示用户 ===")
    
    try:
        async with AsyncSessionLocal() as db:
            from app.services.session_service import SessionService
            from app.schemas.user import UserCreate
            
            # 检查用户是否存在
            existing_user = await SessionService.get_user_by_username(db, "demo")
            if existing_user:
                logger.info("演示用户demo已存在，更新密码...")
                # 直接更新密码
                new_hash = get_password_hash("demo123")
                existing_user.password_hash = new_hash
                await db.commit()
                logger.info("✅ 演示用户密码已更新")
            else:
                logger.info("创建演示用户demo...")
                user_data = UserCreate(
                    username="demo",
                    email="demo@example.com",
                    password="demo123"
                )
                
                user = await SessionService.register_user(db, user_data)
                logger.info(f"✅ 演示用户创建成功: {user.username}")
                
    except Exception as e:
        logger.error(f"❌ 创建演示用户失败: {e}")
        import traceback
        traceback.print_exc()

async def test_password_functions():
    """测试密码函数"""
    logger.info("=== 测试密码函数 ===")
    
    test_passwords = [
        "demo123",
        "a" * 100,  # 超长密码
        "中文密码测试",
        "password_with_special_chars!@#$%^&*()"
    ]
    
    for pwd in test_passwords:
        try:
            # 测试密码哈希生成
            hash_result = get_password_hash(pwd)
            logger.info(f"✅ 密码哈希生成成功: {pwd[:20]}... -> {hash_result[:20]}...")
            
            # 测试密码验证
            verify_result = verify_password(pwd, hash_result)
            logger.info(f"✅ 密码验证成功: {pwd[:20]}... -> {verify_result}")
            
        except Exception as e:
            logger.error(f"❌ 密码测试失败: {pwd[:20]}... -> {e}")

async def main():
    """主函数"""
    logger.info("开始修复密码长度问题...")
    
    # 测试密码函数
    await test_password_functions()
    
    # 创建演示用户
    await create_demo_user()
    
    # 检查和修复现有密码
    await check_and_fix_passwords()
    
    logger.info("\n=== 修复完成 ===")
    logger.info("测试账户信息:")
    logger.info("  用户名: demo")
    logger.info("  密码: demo123")
    logger.info("\n如果问题仍然存在，请检查:")
    logger.info("1. 数据库连接是否正常")
    logger.info("2. bcrypt库版本是否兼容")
    logger.info("3. 系统字符编码设置")

if __name__ == "__main__":
    asyncio.run(main())
