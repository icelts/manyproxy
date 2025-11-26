#!/usr/bin/env python3
"""
检查特定订单的状态
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal
from app.models.proxy import ProxyOrder
from sqlalchemy.future import select

async def check_proxy_order():
    """检查特定订单"""
    print("🔍 检查订单 STATIC_3F23BDA44961...")
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ProxyOrder).where(ProxyOrder.order_id == 'STATIC_3F23BDA44961')
        )
        proxy_order = result.scalar_one_or_none()
        
        if proxy_order:
            print(f"✅ 找到订单:")
            print(f"   订单ID: {proxy_order.order_id}")
            print(f"   上游ID: {proxy_order.upstream_id}")
            print(f"   状态: {proxy_order.status}")
            print(f"   到期时间: {proxy_order.expires_at}")
            print(f"   代理信息: {proxy_order.proxy_info}")
            print(f"   代理信息类型: {type(proxy_order.proxy_info)}")
            
            if proxy_order.proxy_info and isinstance(proxy_order.proxy_info, dict):
                print("   代理信息字段:")
                for key, value in proxy_order.proxy_info.items():
                    print(f"     {key}: {value}")
                    
                # 检查关键字段
                key_fields = ['idproxy', 'ip', 'port', 'user', 'password']
                missing_fields = []
                for field in key_fields:
                    if field not in proxy_order.proxy_info or proxy_order.proxy_info[field] is None:
                        missing_fields.append(field)
                
                if missing_fields:
                    print(f"   ❌ 缺失的关键字段: {missing_fields}")
                else:
                    print("   ✅ 所有关键字段都存在")
            else:
                print("   ❌ 代理信息为空或格式不正确")
        else:
            print("❌ 未找到订单 STATIC_3F23BDA44961")

if __name__ == "__main__":
    asyncio.run(check_proxy_order())
