#!/usr/bin/env python3
"""
清空MySQL数据库脚本
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.core.database import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clear_mysql_database():
    """清空MySQL数据库"""
    mysql_url = settings.DATABASE_URL
    engine = create_async_engine(
        mysql_url,
        echo=True,
        future=True,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            # 禁用外键检查
            await session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            # 获取所有表名
            result = await session.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            
            # 删除所有表
            for table in tables:
                await session.execute(text(f"DROP TABLE IF EXISTS {table}"))
                logger.info(f"已删除表: {table}")
            
            # 重新启用外键检查
            await session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            
            await session.commit()
            logger.info("MySQL数据库已清空")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"清空数据库时发生错误: {e}")
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(clear_mysql_database())
