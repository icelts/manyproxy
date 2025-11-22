#!/usr/bin/env python3
"""
Create test data (SQLite)
"""

import asyncio
import sys
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.models.proxy import ProxyProduct
from app.models.user import User
from app.core.database import Base
from app.core.security import get_password_hash


def hashed(password: str) -> str:
    """Use same password hashing as the app."""
    return get_password_hash(password)


# SQLite DB URL
DATABASE_URL = "sqlite+aiosqlite:///./manyproxy.db"

# Predefined proxy products
PROXY_PRODUCTS = [
    # Static - Vietnam residential (home)
    {
        "category": "static",
        "subcategory": "home",
        "provider": "Viettel",
        "product_name": "Viettel Proxy",
        "description": "Vietnam residential static proxy - Viettel.",
        "price": Decimal("15.00"),
        "duration_days": 30,
        "stock": 100,
        "is_active": True,
    },
    {
        "category": "static",
        "subcategory": "home",
        "provider": "FPT",
        "product_name": "FPT Proxy",
        "description": "Vietnam residential static proxy - FPT.",
        "price": Decimal("12.00"),
        "duration_days": 30,
        "stock": 100,
        "is_active": True,
    },
    {
        "category": "static",
        "subcategory": "home",
        "provider": "VNPT",
        "product_name": "VNPT Proxy",
        "description": "Vietnam residential static proxy - VNPT.",
        "price": Decimal("13.00"),
        "duration_days": 30,
        "stock": 100,
        "is_active": True,
    },
    # Static - Vietnam datacenter
    {
        "category": "static",
        "subcategory": "vn_datacenter",
        "provider": "DatacenterA",
        "product_name": "DatacenterA Proxy",
        "description": "Vietnam datacenter proxy - low latency, high performance.",
        "price": Decimal("8.00"),
        "duration_days": 30,
        "stock": 200,
        "is_active": True,
    },
    {
        "category": "static",
        "subcategory": "vn_datacenter",
        "provider": "DatacenterB",
        "product_name": "DatacenterB Proxy",
        "description": "Vietnam datacenter proxy - stable and reliable.",
        "price": Decimal("7.50"),
        "duration_days": 30,
        "stock": 200,
        "is_active": True,
    },
    # Static - US datacenter
    {
        "category": "static",
        "subcategory": "us_datacenter",
        "provider": "USDatacenter",
        "product_name": "US Proxy",
        "description": "US datacenter proxy - suitable for overseas workloads.",
        "price": Decimal("10.00"),
        "duration_days": 30,
        "stock": 150,
        "is_active": True,
    },
    # Static - home packages
    {
        "category": "static",
        "subcategory": "home",
        "provider": "Viettel",
        "product_name": "Viettel Package",
        "description": "Residential proxy package.",
        "price": Decimal("1200.00"),
        "duration_days": 30,
        "stock": 10,
        "is_active": True,
    },
    {
        "category": "static",
        "subcategory": "home",
        "provider": "FPT",
        "product_name": "FPT Package",
        "description": "Residential proxy package.",
        "price": Decimal("960.00"),
        "duration_days": 30,
        "stock": 10,
        "is_active": True,
    },
    {
        "category": "static",
        "subcategory": "home",
        "provider": "VNPT",
        "product_name": "VNPT Package",
        "description": "Residential proxy package.",
        "price": Decimal("1040.00"),
        "duration_days": 30,
        "stock": 10,
        "is_active": True,
    },
]

# Test users
TEST_USERS = [
    {
        "username": "admin",
        "email": "admin@manyproxy.com",
        "password_hash": hashed("admin123"),
        "is_active": True,
        "is_admin": True,
        "balance": Decimal("1000.00"),
    },
    {
        "username": "demo",
        "email": "demo@manyproxy.com",
        "password_hash": hashed("demo123"),
        "is_active": True,
        "is_admin": False,
        "balance": Decimal("100.00"),
    },
    {
        "username": "testuser",
        "email": "test@manyproxy.com",
        "password_hash": hashed("test123"),
        "is_active": True,
        "is_admin": False,
        "balance": Decimal("50.00"),
    },
]


async def create_test_data():
    """Create test data."""
    print("== Creating test data ==")

    # Create DB engine
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Create all tables (for local SQLite test data)
    print("Creating DB tables (SQLite)...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        try:
            # 1. Users
            print("\nCreating users...")
            created_users = 0
            for user_data in TEST_USERS:
                result = await db.execute(select(User).where(User.username == user_data["username"]))
                existing_user = result.scalar_one_or_none()

                if not existing_user:
                    user = User(**user_data)
                    db.add(user)
                    created_users += 1
                    print(f"  + user: {user_data['username']}")
                else:
                    print(f"  = exists: {user_data['username']}")

            # 2. Products
            print("\nCreating proxy products...")
            created_products = 0
            for product_data in PROXY_PRODUCTS:
                result = await db.execute(
                    select(ProxyProduct).where(ProxyProduct.product_name == product_data["product_name"])
                )
                existing_product = result.scalar_one_or_none()

                if not existing_product:
                    product = ProxyProduct(**product_data)
                    db.add(product)
                    created_products += 1
                    print(f"  + product: {product_data['product_name']}")
                else:
                    print(f"  = exists: {product_data['product_name']}")

            await db.commit()

            print("\nDone.")
            print(f"  users created  : {created_users}")
            print(f"  products created: {created_products}")

            # Summary
            print("\nSummary:")
            result = await db.execute(select(User))
            users = result.scalars().all()
            print(f"  total users: {len(users)}")

            result = await db.execute(select(ProxyProduct))
            products = result.scalars().all()
            print(f"  total products: {len(products)}")

        except Exception as e:
            print(f"Failed to create test data: {e}")
            await db.rollback()
            raise
        finally:
            await engine.dispose()


async def main():
    """Main."""
    try:
        await create_test_data()
        print("\nTest data created successfully.")
        print("\nTest accounts:")
        print("  Admin: admin / admin123")
        print("  Demo : demo / demo123")
        print("  Test : testuser / test123")
    except Exception as e:
        print(f"\nFailed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("ManyProxy Test Data Creator")
    print("=" * 60)
    asyncio.run(main())

