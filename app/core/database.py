from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_recycle=3600,  # MySQL connection pool recycle (seconds)
    pool_pre_ping=True,  # Pre-ping to check connection liveness
)

# Async session factory
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Declarative base
Base = declarative_base()


# Initialize database schema (guarded; for local/dev only)
async def init_db():
    """Initialize database schema via create_all (not recommended for production)."""
    if not settings.ALLOW_DB_CREATE_ALL:
        logger.warning(
            "init_db skipped because ALLOW_DB_CREATE_ALL is False. Use Alembic migrations in production."
        )
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Dependency: db session
async def get_db() -> AsyncSession:
    """
    Yield an async DB session, commit on success and rollback on error.
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

