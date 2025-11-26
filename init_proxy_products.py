#!/usr/bin/env python3
"""
初始化代理产品数据脚本
根据用户需求预定义代理产品
"""

import asyncio
import sys
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.proxy import ProxyProduct

# 预定义的代理产品数据
PROXY_PRODUCTS = [
    # 静态代理 - 越南静态家庭代理
    {
        "category": "static",
        "subcategory": "home",
        "provider": "Viettel",
        "product_name": "Viettel 静态家庭代理",
        "description": "越南Viettel运营商静态家庭代理，稳定可靠，适合长期使用",
        "price": Decimal("15.00"),
        "price_30": Decimal("15.00"),
        "price_60": Decimal("28.00"),
        "price_90": Decimal("40.00"),
        "duration_days": 30,
        "stock": 100,
        "is_active": True
    },
    {
        "category": "static",
        "subcategory": "home",
        "provider": "FPT",
        "product_name": "FPT 静态家庭代理",
        "description": "越南FPT运营商静态家庭代理，速度快，性能优秀",
        "price": Decimal("12.00"),
        "price_30": Decimal("12.00"),
        "price_60": Decimal("23.00"),
        "price_90": Decimal("34.00"),
        "duration_days": 30,
        "stock": 100,
        "is_active": True
    },
    {
        "category": "static",
        "subcategory": "home",
        "provider": "VNPT",
        "product_name": "VNPT 静态家庭代理",
        "description": "越南VNPT运营商静态家庭代理，覆盖面广",
        "price": Decimal("13.00"),
        "price_30": Decimal("13.00"),
        "price_60": Decimal("25.00"),
        "price_90": Decimal("36.00"),
        "duration_days": 30,
        "stock": 100,
        "is_active": True
    },
    
    # 静态代理 - 静态越南机房代理
    {
        "category": "static",
        "subcategory": "vn_datacenter",
        "provider": "DatacenterA",
        "product_name": "越南机房代理A",
        "description": "越南数据中心机房代理，高性能，低延迟",
        "price": Decimal("8.00"),
        "duration_days": 30,
        "stock": 200,
        "is_active": True
    },
    {
        "category": "static",
        "subcategory": "vn_datacenter",
        "provider": "DatacenterB",
        "product_name": "越南机房代理B",
        "description": "越南数据中心机房代理，稳定可靠",
        "price": Decimal("7.50"),
        "duration_days": 30,
        "stock": 200,
        "is_active": True
    },
    
    # 静态代理 - 静态美国机房代理
    {
        "category": "static",
        "subcategory": "us_datacenter",
        "provider": "USDatacenter",
        "product_name": "美国机房代理",
        "description": "美国数据中心机房代理，适合海外业务",
        "price": Decimal("10.00"),
        "duration_days": 30,
        "stock": 150,
        "is_active": True
    },
    
    # 静态家庭代理包
    {
        "category": "static",
        "subcategory": "home",
        "provider": "Viettel",
        "product_name": "Viettel 静态家庭代理包 (90-96个)",
        "description": "Viettel静态家庭代理包，包含90-96个代理IP，根据运营商分配不同价格",
        "price": Decimal("1200.00"),
        "duration_days": 30,
        "stock": 10,
        "is_active": True
    },
    {
        "category": "static",
        "subcategory": "home",
        "provider": "FPT",
        "product_name": "FPT 静态家庭代理包 (90-96个)",
        "description": "FPT静态家庭代理包，包含90-96个代理IP，根据运营商分配不同价格",
        "price": Decimal("960.00"),
        "duration_days": 30,
        "stock": 10,
        "is_active": True
    },
    {
        "category": "static",
        "subcategory": "home",
        "provider": "VNPT",
        "product_name": "VNPT 静态家庭代理包 (90-96个)",
        "description": "VNPT静态家庭代理包，包含90-96个代理IP，根据运营商分配不同价格",
        "price": Decimal("1040.00"),
        "duration_days": 30,
        "stock": 10,
        "is_active": True
    },
    
    # 动态家庭代理
    {
        "category": "dynamic",
        "subcategory": "home",
        "provider": "DynamicVietnam",
        "product_name": "越南动态家庭代理",
        "description": "越南动态家庭代理，IP自动轮换，适合需要频繁更换IP的业务",
        "price": Decimal("25.00"),
        "duration_days": 30,
        "stock": 50,
        "is_active": True
    },
    
    # 移动手机代理
    {
        "category": "mobile",
        "subcategory": "mobile",
        "provider": "VietnamMobile",
        "product_name": "越南移动手机代理",
        "description": "越南移动手机代理，真实移动网络IP，高质量代理服务",
        "price": Decimal("35.00"),
        "duration_days": 30,
        "stock": 30,
        "is_active": True
    }
]


async def init_proxy_products():
    """初始化代理产品数据"""
    print("开始初始化代理产品数据...")
    
    # 获取数据库会话
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        # 检查是否已有产品数据
        result = await db.execute(select(ProxyProduct))
        existing_products = result.scalars().all()
        
        if existing_products:
            print(f"发现 {len(existing_products)} 个现有产品，将清空并重新初始化...")
            # 清空现有产品
            for product in existing_products:
                await db.delete(product)
            await db.commit()
            print("已清空现有产品数据")
        
        # 批量创建新产品
        created_count = 0
        for product_data in PROXY_PRODUCTS:
            product = ProxyProduct(**product_data)
            db.add(product)
            created_count += 1
        
        await db.commit()
        print(f"成功创建 {created_count} 个代理产品")
        
        # 按类别统计
        result = await db.execute(
            select(ProxyProduct.category, func.count(ProxyProduct.id))
            .group_by(ProxyProduct.category)
        )
        categories = result.all()
        
        print("\n产品统计:")
        for category, count in categories:
            print(f"  {category}: {count} 个产品")
        
        print("\n初始化完成！")
        
    except Exception as e:
        print(f"初始化失败: {e}")
        await db.rollback()
        raise
    finally:
        await db.close()


async def main():
    """主函数"""
    try:
        await init_proxy_products()
        print("\n✅ 代理产品初始化成功！")
        print("\n现在可以在管理后台查看代理产品了。")
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 导入必要的模块
    from sqlalchemy import func
    
    print("=" * 60)
    print("代理产品初始化脚本")
    print("=" * 60)
    print("\n将创建以下代理产品:")
    print("1. 静态代理")
    print("   - 越南静态家庭代理 (Viettel, FPT, VNPT)")
    print("   - 静态越南机房代理")
    print("   - 静态美国机房代理")
    print("   - 静态家庭代理包 (90-96个IP)")
    print("2. 动态家庭代理")
    print("   - 越南动态家庭代理")
    print("3. 移动手机代理")
    print("   - 越南移动手机代理")
    print("\n所有代理产品购买时长为30天，不限制流量")
    print("=" * 60)
    
    # 确认执行
    confirm = input("\n确认执行初始化? (y/N): ").strip().lower()
    if confirm in ['y', 'yes']:
        asyncio.run(main())
    else:
        print("已取消初始化")
