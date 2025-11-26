#!/usr/bin/env python3
"""
SQLite到MySQL数据迁移脚本
"""

import sqlite3
import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base
from app.models.user import User, APIKey
from app.models.proxy import ProxyProduct, ProxyOrder, APIUsage, UpstreamProvider, ProductMapping
from app.models.order import Order, Payment, Transaction, BalanceLog
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLiteToMySQLMigrator:
    def __init__(self):
        self.sqlite_db = 'manyproxy.db'
        self.mysql_engine = None
        
    async def init_mysql_connection(self):
        """初始化MySQL连接"""
        # 使用配置文件中的MySQL连接字符串
        mysql_url = settings.DATABASE_URL
        self.mysql_engine = create_async_engine(
            mysql_url,
            echo=True,
            future=True,
            pool_recycle=3600,
            pool_pre_ping=True,
        )
        
        # 创建所有表
        async with self.mysql_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("MySQL数据库连接初始化完成，表结构已创建")
        
    def export_sqlite_data(self):
        """从SQLite导出所有数据"""
        conn = sqlite3.connect(self.sqlite_db)
        conn.row_factory = sqlite3.Row
        
        data = {}
        
        try:
            # 获取所有表名
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table_name in tables:
                if table_name == 'sqlite_sequence':
                    continue
                    
                logger.info(f"正在导出表: {table_name}")
                cursor = conn.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                table_data = []
                for row in rows:
                    row_data = dict(row)
                    # 转换日期时间格式
                    for key, value in row_data.items():
                        if value and key.endswith('_at'):
                            if isinstance(value, str):
                                try:
                                    row_data[key] = datetime.fromisoformat(value)
                                except:
                                    pass
                        elif value and key in ['provider_config', 'proxy_info', 'config', 'upstream_params']:
                            if isinstance(value, str):
                                try:
                                    row_data[key] = json.loads(value)
                                except:
                                    pass
                    table_data.append(row_data)
                
                data[table_name] = table_data
                logger.info(f"  {table_name}: {len(table_data)} 条记录")
            
            return data
            
        finally:
            conn.close()
    
    async def import_to_mysql(self, data):
        """将数据导入MySQL"""
        AsyncSessionLocal = sessionmaker(self.mysql_engine, class_=AsyncSession, expire_on_commit=False)
        
        # 模型映射
        model_mapping = {
            'users': User,
            'api_keys': APIKey,
            'proxy_products': ProxyProduct,
            'proxy_orders': ProxyOrder,
            'api_usage': APIUsage,
            'upstream_providers': UpstreamProvider,
            'product_mappings': ProductMapping,
            'orders': Order,
            'payments': Payment,
            'transactions': Transaction,
            'balance_logs': BalanceLog,
        }
        
        async with AsyncSessionLocal() as session:
            try:
                for table_name, records in data.items():
                    if table_name not in model_mapping:
                        logger.warning(f"跳过未知表: {table_name}")
                        continue
                        
                    if not records:
                        logger.info(f"表 {table_name} 没有数据，跳过")
                        continue
                        
                    model_class = model_mapping[table_name]
                    valid_records = []
                    
                    for record_data in records:
                        try:
                            # 处理特殊字段映射
                            if table_name == 'proxy_products':
                                # 移除旧的price字段
                                record_data = {k: v for k, v in record_data.items() 
                                             if not k.startswith('price_') and k != 'provider_config'}
                            elif table_name == 'proxy_orders':
                                # 检查product_id是否存在
                                product_ids = [r['id'] for r in data.get('proxy_products', [])]
                                if record_data.get('product_id') and record_data['product_id'] not in product_ids:
                                    logger.warning(f"跳过proxy_orders记录，product_id {record_data['product_id']} 不存在")
                                    continue
                            
                            # 创建模型实例
                            record = model_class(**record_data)
                            valid_records.append(record)
                            
                        except Exception as e:
                            logger.error(f"导入 {table_name} 记录时出错: {e}")
                            logger.error(f"记录数据: {record_data}")
                            continue
                    
                    # 批量添加有效记录
                    for record in valid_records:
                        session.add(record)
                    
                    await session.commit()
                    logger.info(f"已导入 {len(valid_records)} 条 {table_name} 记录")
                
                logger.info("所有数据已成功导入MySQL数据库")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"导入数据时发生错误: {e}")
                raise
            finally:
                await session.close()
    
    async def migrate(self):
        """执行完整的迁移过程"""
        try:
            logger.info("开始SQLite到MySQL数据迁移...")
            
            # 1. 初始化MySQL连接
            await self.init_mysql_connection()
            
            # 2. 从SQLite导出数据
            logger.info("正在从SQLite导出数据...")
            data = self.export_sqlite_data()
            
            # 3. 导入到MySQL
            logger.info("正在导入数据到MySQL...")
            await self.import_to_mysql(data)
            
            logger.info("数据迁移完成！")
            
        except Exception as e:
            logger.error(f"迁移过程中发生错误: {e}")
            raise
        finally:
            if self.mysql_engine:
                await self.mysql_engine.dispose()

async def main():
    """主函数"""
    migrator = SQLiteToMySQLMigrator()
    await migrator.migrate()

if __name__ == "__main__":
    asyncio.run(main())
