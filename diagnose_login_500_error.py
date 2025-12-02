#!/usr/bin/env python3
"""
登录500错误诊断和修复脚本
分析宝塔面板部署时的登录问题并提供解决方案
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal
from app.models.user import User
from sqlalchemy import text
from app.utils.cache import init_redis

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def diagnose_database_connection():
    """诊断数据库连接"""
    logger.info("=== 数据库连接诊断 ===")
    
    try:
        # 测试数据库连接
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            logger.info(f"✅ 数据库连接成功: {settings.DATABASE_URL}")
            
            # 检查用户表是否存在
            try:
                result = await conn.execute(text("DESCRIBE users"))
                logger.info("✅ users表结构正常")
            except Exception as e:
                logger.error(f"❌ users表问题: {e}")
                
            # 检查测试用户是否存在
            try:
                result = await conn.execute(text("SELECT COUNT(*) FROM users WHERE username = 'demo'"))
                count = result.scalar()
                if count > 0:
                    logger.info("✅ 测试用户demo存在")
                else:
                    logger.warning("⚠️ 测试用户demo不存在")
            except Exception as e:
                logger.error(f"❌ 查询测试用户失败: {e}")
                
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False
    
    return True

async def diagnose_redis_connection():
    """诊断Redis连接"""
    logger.info("=== Redis连接诊断 ===")
    
    try:
        await init_redis()
        logger.info("✅ Redis连接成功")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Redis连接失败: {e}")
        logger.info("注意: Redis连接失败不会影响登录功能，系统会使用内存缓存")
        return False

async def diagnose_login_flow():
    """诊断登录流程"""
    logger.info("=== 登录流程诊断 ===")
    
    try:
        async with AsyncSessionLocal() as db:
            # 测试用户查询
            from app.services.session_service import SessionService
            
            # 测试认证
            user = await SessionService.authenticate_credentials(db, "demo", "demo123")
            if user:
                logger.info("✅ 用户认证成功")
                
                # 测试会话构建
                try:
                    envelope = await SessionService.build_session_envelope(user, db=db)
                    logger.info("✅ 会话构建成功")
                    logger.info(f"用户ID: {envelope.user.id}")
                    logger.info(f"用户名: {envelope.user.username}")
                    logger.info(f"API密钥: {envelope.api_key[:10] + '...' if envelope.api_key else 'None'}")
                except Exception as e:
                    logger.error(f"❌ 会话构建失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                logger.warning("⚠️ 用户认证失败 - 用户名或密码错误")
                return False
                
    except Exception as e:
        logger.error(f"❌ 登录流程诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def check_environment_variables():
    """检查环境变量"""
    logger.info("=== 环境变量检查 ===")
    
    critical_vars = {
        'DATABASE_URL': settings.DATABASE_URL,
        'SECRET_KEY': settings.SECRET_KEY,
        'DEBUG': settings.DEBUG,
    }
    
    for var_name, var_value in critical_vars.items():
        if var_value:
            if var_name == 'SECRET_KEY':
                logger.info(f"✅ {var_name}: {'*' * 10}...{var_value[-10:]}")
            else:
                logger.info(f"✅ {var_name}: {var_value}")
        else:
            logger.error(f"❌ {var_name}: 未设置")

async def create_test_user_if_needed():
    """创建测试用户（如果需要）"""
    logger.info("=== 测试用户检查 ===")
    
    try:
        async with AsyncSessionLocal() as db:
            from app.services.session_service import SessionService
            from app.schemas.user import UserCreate
            
            # 检查用户是否存在
            existing_user = await SessionService.get_user_by_username(db, "demo")
            if existing_user:
                logger.info("✅ 测试用户demo已存在")
                return True
            
            # 创建测试用户
            logger.info("创建测试用户demo...")
            user_data = UserCreate(
                username="demo",
                email="demo@example.com",
                password="demo123"
            )
            
            user = await SessionService.register_user(db, user_data)
            logger.info(f"✅ 测试用户创建成功: {user.username}")
            return True
            
    except Exception as e:
        logger.error(f"❌ 创建测试用户失败: {e}")
        return False

async def main():
    """主诊断函数"""
    logger.info("开始登录500错误诊断...")
    logger.info(f"当前环境: {'生产环境' if not settings.DEBUG else '开发环境'}")
    
    # 检查环境变量
    await check_environment_variables()
    
    # 诊断数据库连接
    db_ok = await diagnose_database_connection()
    
    # 诊断Redis连接
    await diagnose_redis_connection()
    
    # 创建测试用户（如果需要）
    if db_ok:
        await create_test_user_if_needed()
        
        # 诊断登录流程
        login_ok = await diagnose_login_flow()
        
        if login_ok:
            logger.info("🎉 登录流程诊断完成 - 一切正常!")
        else:
            logger.error("❌ 登录流程存在问题")
    else:
        logger.error("❌ 数据库连接问题，无法继续诊断")
    
    logger.info("\n=== 常见问题解决方案 ===")
    logger.info("1. 如果Redis连接失败:")
    logger.info("   - 检查Redis服务是否启动: systemctl status redis")
    logger.info("   - 检查Redis配置: /etc/redis/redis.conf")
    logger.info("   - 或者忽略此警告，系统会自动降级到内存缓存")
    
    logger.info("\n2. 如果数据库连接失败:")
    logger.info("   - 检查MySQL服务: systemctl status mysql")
    logger.info("   - 检查数据库连接字符串")
    logger.info("   - 确保数据库用户有足够权限")
    
    logger.info("\n3. 如果登录仍然失败:")
    logger.info("   - 检查防火墙设置")
    logger.info("   - 检查宝塔面板的SSL证书配置")
    logger.info("   - 查看应用日志: tail -f logs/app.log")
    
    logger.info("\n4. 测试账户信息:")
    logger.info("   用户名: demo")
    logger.info("   密码: demo123")

if __name__ == "__main__":
    asyncio.run(main())
