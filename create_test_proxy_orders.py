#!/usr/bin/env python3
"""
创建测试代理订单数据
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal
from app.models.user import User, APIKey
from app.models.proxy import ProxyOrder, ProxyProduct
from sqlalchemy import select

async def create_test_proxy_orders():
    """创建测试代理订单"""
    async with AsyncSessionLocal() as db:
        # 查找测试用户
        result = await db.execute(
            select(User).where(User.username == 'testuser')
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ 测试用户不存在，请先运行 create_test_api_key_simple.py")
            return False
        
        print(f"✅ 使用测试用户: {user.username} (ID: {user.id})")
        
        # 创建测试产品（如果不存在）
        static_product = await db.execute(
            select(ProxyProduct).where(ProxyProduct.product_name == "Test Static Proxy")
        )
        static_product = static_product.scalar_one_or_none()
        
        if not static_product:
            static_product = ProxyProduct(
                category="static",
                subcategory="test",
                provider="TestProvider",
                product_name="Test Static Proxy",
                description="测试静态代理产品",
                price=10.0,
                duration_days=30,
                stock=100,
                is_active=True
            )
            db.add(static_product)
            await db.flush()
            print(f"✅ 创建静态代理产品: {static_product.product_name}")
        
        dynamic_product = await db.execute(
            select(ProxyProduct).where(ProxyProduct.product_name == "Test Dynamic Proxy")
        )
        dynamic_product = dynamic_product.scalar_one_or_none()
        
        if not dynamic_product:
            dynamic_product = ProxyProduct(
                category="dynamic",
                subcategory="test",
                provider="TestProvider",
                product_name="Test Dynamic Proxy",
                description="测试动态代理产品",
                price=20.0,
                duration_days=30,
                stock=100,
                is_active=True
            )
            db.add(dynamic_product)
            await db.flush()
            print(f"✅ 创建动态代理产品: {dynamic_product.product_name}")
        
        # 创建测试代理订单
        current_time = datetime.now()
        
        # 静态代理订单
        static_order = ProxyOrder(
            user_id=user.id,
            product_id=static_product.id,
            order_id=f"STATIC_{current_time.strftime('%Y%m%d_%H%M%S')}",
            upstream_id="upstream_static_123",
            proxy_info={
                "ip": "192.168.1.100",
                "port": 8080,
                "username": "user1",
                "password": "pass1",
                "type": "http"
            },
            status="active",
            created_at=current_time,
            expires_at=current_time + timedelta(days=30)
        )
        db.add(static_order)
        
        # 动态代理订单
        dynamic_order = ProxyOrder(
            user_id=user.id,
            product_id=dynamic_product.id,
            order_id="export",  # 特殊订单ID用于测试导出功能
            upstream_id="upstream_dynamic_456",
            proxy_info={
                "endpoint": "http://dynamic.example.com",
                "auth_token": "token123",
                "type": "dynamic"
            },
            status="active",
            created_at=current_time,
            expires_at=current_time + timedelta(days=30)
        )
        db.add(dynamic_order)
        
        # 过期的静态代理订单
        expired_static_order = ProxyOrder(
            user_id=user.id,
            product_id=static_product.id,
            order_id=f"STATIC_EXPIRED_{current_time.strftime('%Y%m%d_%H%M%S')}",
            upstream_id="upstream_static_789",
            proxy_info={
                "ip": "192.168.1.101",
                "port": 8080,
                "username": "user2",
                "password": "pass2",
                "type": "http"
            },
            status="expired",
            created_at=current_time - timedelta(days=60),
            expires_at=current_time - timedelta(days=30)
        )
        db.add(expired_static_order)
        
        await db.commit()
        
        print(f"✅ 创建测试代理订单:")
        print(f"   - 静态代理: {static_order.order_id}")
        print(f"   - 动态代理: {dynamic_order.order_id}")
        print(f"   - 过期静态代理: {expired_static_order.order_id}")
        
        return True

if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 运行创建
    try:
        success = asyncio.run(create_test_proxy_orders())
        if success:
            print(f"\n🎉 测试数据创建成功！现在可以运行 test_proxy_new_features.py")
        else:
            print(f"\n❌ 测试数据创建失败")
    except Exception as e:
        print(f"❌ 创建测试数据失败: {e}")
        import traceback
        traceback.print_exc()
