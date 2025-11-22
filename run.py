#!/usr/bin/env python3
"""
ManyProxy startup script
 - Runs Alembic migrations
 - Seeds default users for development
 - Starts the application (optional)
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import init_db, get_db  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402
import alembic.config  # noqa: E402
import alembic.command  # noqa: E402


async def create_admin_user():
    """Create default admin user if not exists."""
    print("Ensuring default admin user...")

    async for db in get_db():
        from sqlalchemy.future import select

        result = await db.execute(select(User).where(User.is_admin == True))  # noqa: E712
        admin_user = result.scalar_one_or_none()

        if admin_user:
            print("Admin user already exists.")
            break

        from datetime import datetime

        admin_user = User(
            username="admin",
            email="admin@manyproxy.com",
            password_hash=get_password_hash("admin123"),
            balance=1000.00,
            is_admin=True,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)

        print(f"Created admin user: {admin_user.username}")
        print("Default password: admin123 (CHANGE IMMEDIATELY IN PRODUCTION)")
        break


async def create_demo_user():
    """Create demo user if not exists."""
    print("Ensuring demo user...")

    async for db in get_db():
        from sqlalchemy.future import select

        result = await db.execute(select(User).where(User.username == "demo"))
        demo_user = result.scalar_one_or_none()

        if demo_user:
            print("Demo user already exists.")
            break

        from datetime import datetime

        demo_user = User(
            username="demo",
            email="demo@manyproxy.com",
            password_hash=get_password_hash("demo123"),
            balance=100.00,
            is_admin=False,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(demo_user)
        await db.commit()
        await db.refresh(demo_user)

        print(f"Created demo user: {demo_user.username}")
        print("Default password: demo123")
        break


async def init_database():
    """Run Alembic migrations (preferred). Optionally create tables for dev."""
    print("Running database migrations...")

    try:
        alembic_cfg = alembic.config.Config("alembic.ini")
        alembic.command.upgrade(alembic_cfg, "head")
        print("Migrations completed.")
    except Exception as e:
        print(f"Migration failed: {e}")
        # Optional fallback for local development only
        if os.getenv("ALLOW_DB_CREATE_ALL", "").lower() in ("1", "true", "yes"):
            await init_db()
            print("Database initialized via create_all (development fallback).")
        else:
            raise

    # Seed default users (dev convenience)
    await create_admin_user()
    await create_demo_user()


def print_startup_info():
    """Print startup info."""
    print("\n" + "=" * 50)
    print("ManyProxy")
    print("=" * 50)
    print("\nDefault accounts (development):")
    print("Admin: admin / admin123")
    print("Demo : demo / demo123")
    print("\nURLs:")
    print("Frontend: http://localhost:8000/frontend/index.html")
    print("Docs    : http://localhost:8000/api/v1/docs")
    print("=" * 50 + "\n")


async def main():
    """Main entry."""
    import argparse

    parser = argparse.ArgumentParser(description="ManyProxy runner")
    parser.add_argument("--init-db", action="store_true", help="Only run DB migrations/initialization and exit")
    parser.add_argument("--host", default="0.0.0.0", help="Host")
    parser.add_argument("--port", type=int, default=8000, help="Port")
    parser.add_argument("--reload", action="store_true", help="Enable reload (dev)")

    args = parser.parse_args()

    if args.init_db:
        await init_database()
        print("Database initialization done.")
        return

    # Initialize database
    await init_database()

    # Print startup info
    print_startup_info()

    # Start app
    import uvicorn
    from app.main import app

    config = uvicorn.Config(
        app=app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
        log_config=None,
    )

    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:
        print(f"Startup failed: {e}")
        sys.exit(1)
