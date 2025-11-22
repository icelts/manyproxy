from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from alembic import context
import asyncio
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入项目配置和模型
from app.core.config import settings
from app.core.database import Base
from app.models.user import User
from app.models.proxy import ProxyProduct, ProxyOrder, APIUsage
from app.models.order import Order, Payment, Transaction, BalanceLog

# 这是Alembic Config对象，提供对.ini文件中值的访问。
config = context.config

# 设置数据库URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 解释记录器配置的配置文件。
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 添加你的模型的MetaData对象
# 用于'autogenerate'支持
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """在'offline'模式下运行迁移。

    这配置了上下文，只使用URL，不使用Engine，
    尽管这里也接受Engine。通过跳过Engine创建，
    我们甚至不需要DBAPI可用。

    在这里调用context.execute()会发出给定的字符串到脚本输出。

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在'online'模式下运行迁移。

    在这种情况下，我们需要创建一个Engine并关联一个连接。

    """
    # 对于异步数据库，我们需要使用同步版本的URL进行迁移
    # 将 sqlite+aiosqlite:// 转换为 sqlite:///
    sync_url = settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///")
    # 如果是MySQL，将 mysql+aiomysql:// 转换为 mysql+pymysql://
    sync_url = sync_url.replace("mysql+aiomysql://", "mysql+pymysql://")
    
    connectable = engine_from_config(
        {**config.get_section(config.config_ini_section, {}), "sqlalchemy.url": sync_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
