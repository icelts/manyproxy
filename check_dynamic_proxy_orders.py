#!/usr/bin/env python3
"""
检查动态代理订单数据
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal
from app.models.proxy import ProxyOrder
from sqlalchemy.future import select
import json

async def check_dynamic_proxy_orders():
    """检查动态代理订单数据"""
    
    print("=" * 60)
    print("检查动态代理订单数据")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        # 查询所有动态代理订单
        result = await db.execute(
            select(ProxyOrder).where(ProxyOrder.order_id.like("DYNAMIC_%"))
        )
        dynamic_orders = result.scalars().all()
        
        print(f"找到 {len(dynamic_orders)} 个动态代理订单:")
        print()
        
        for order in dynamic_orders:
            print(f"订单ID: {order.order_id}")
            print(f"用户ID: {order.user_id}")
            print(f"上游ID: {order.upstream_id}")
            print(f"状态: {order.status}")
            print(f"创建时间: {order.created_at}")
            print(f"过期时间: {order.expires_at}")
            
            # 解析proxy_info
            if order.proxy_info:
                print("代理信息:")
                if isinstance(order.proxy_info, str):
                    try:
                        proxy_info = json.loads(order.proxy_info)
                    except:
                        proxy_info = {"raw": order.proxy_info}
                else:
                    proxy_info = order.proxy_info
                
                for key, value in proxy_info.items():
                    print(f"  {key}: {value}")
            else:
                print("代理信息: 无")
            
            print("-" * 40)
        
        # 检查是否有活跃的动态代理
        active_dynamic = [o for o in dynamic_orders if o.status == "active"]
        print(f"\n活跃的动态代理: {len(active_dynamic)}")
        
        for order in active_dynamic:
            print(f"  {order.order_id}: upstream_id = {order.upstream_id}")

if __name__ == "__main__":
    asyncio.run(check_dynamic_proxy_orders())
