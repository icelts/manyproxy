#!/usr/bin/env python3
"""
创建测试动态代理订单
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal
from app.models.proxy import ProxyOrder
from sqlalchemy.future import select

async def create_test_dynamic_orders():
    """创建测试动态代理订单"""
    
    print("=" * 60)
    print("创建测试动态代理订单")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        # 检查是否已有动态代理订单
        result = await db.execute(
            select(ProxyOrder).where(ProxyOrder.order_id.like("DYNAMIC_%"))
        )
        existing_orders = result.scalars().all()
        
        if existing_orders:
            print(f"已存在 {len(existing_orders)} 个动态代理订单，跳过创建")
            for order in existing_orders:
                print(f"  {order.order_id}: upstream_id = {order.upstream_id}")
            return
        
        # 创建测试动态代理订单
        test_orders = [
            {
                "user_id": 2,  # 测试用户ID
                "product_id": 3,  # 假设的动态代理产品ID
                "order_id": "DYNAMIC_TEST001",
                "upstream_id": "key_dynamic_test_001_abc123def456",
                "proxy_info": {
                    "status": 100,
                    "keyxoay": "key_dynamic_test_001_abc123def456",
                    "comen": "Success",
                    "data": {
                        "key": "key_dynamic_test_001_abc123def456",
                        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat()
                    }
                },
                "status": "active",
                "expires_at": datetime.utcnow() + timedelta(days=30)
            },
            {
                "user_id": 2,
                "product_id": 3,
                "order_id": "DYNAMIC_TEST002",
                "upstream_id": "key_dynamic_test_002_xyz789uvw012",
                "proxy_info": {
                    "status": 100,
                    "keyxoay": "key_dynamic_test_002_xyz789uvw012",
                    "comen": "Success",
                    "data": {
                        "key": "key_dynamic_test_002_xyz789uvw012",
                        "expires_at": (datetime.utcnow() + timedelta(days=60)).isoformat()
                    }
                },
                "status": "active",
                "expires_at": datetime.utcnow() + timedelta(days=60)
            }
        ]
        
        # 添加订单到数据库
        for order_data in test_orders:
            order = ProxyOrder(**order_data)
            db.add(order)
        
        await db.commit()
        
        print(f"成功创建 {len(test_orders)} 个测试动态代理订单:")
        for order in test_orders:
            print(f"  {order['order_id']}: upstream_id = {order['upstream_id']}")

if __name__ == "__main__":
    asyncio.run(create_test_dynamic_orders())
