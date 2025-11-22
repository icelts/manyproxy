#!/usr/bin/env python3
import asyncio
import sys
import os

# Add project root to PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User
from sqlalchemy.future import select


async def reset_admin_password():
    """Reset admin password to 'admin123' (development helper)."""
    async for db in get_db():
        try:
            result = await db.execute(select(User).where(User.username == "admin"))
            admin_user = result.scalar_one_or_none()

            if admin_user:
                new_password = "admin123"
                admin_user.password_hash = get_password_hash(new_password)
                await db.commit()
                print(f"Admin password reset to: {new_password}")
                print(f"Username: {admin_user.username}")
                print(f"Is admin: {admin_user.is_admin}")
                print(f"Active  : {admin_user.is_active}")
            else:
                print("Admin user not found")

        except Exception as e:
            print(f"Failed to reset password: {e}")
            await db.rollback()
        finally:
            await db.close()
        break


if __name__ == "__main__":
    asyncio.run(reset_admin_password())
