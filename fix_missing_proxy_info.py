#!/usr/bin/env python3
"""
修复缺失的代理信息
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal
from app.models.proxy import ProxyOrder, ProxyProduct
from app.services.upstream_api import StaticProxyService
from sqlalchemy.future import select
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_missing_proxy_info():
    """修复缺失的代理信息"""
    print("🔧 修复订单 STATIC_3F23BDA44961 的缺失代理信息...")
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. 查找订单
            result = await db.execute(
                select(ProxyOrder).where(ProxyOrder.order_id == 'STATIC_3F23BDA44961')
            )
            proxy_order = result.scalar_one_or_none()
            
            if not proxy_order:
                print("❌ 未找到订单")
                return
            
            print(f"✅ 找到订单: {proxy_order.order_id}")
            print(f"   当前代理信息: {proxy_order.proxy_info}")
            
            # 2. 查找产品信息
            product_result = await db.execute(
                select(ProxyProduct).where(ProxyProduct.id == proxy_order.product_id)
            )
            product = product_result.scalar_one_or_none()
            
            if not product:
                print("❌ 未找到产品信息")
                return
            
            print(f"✅ 找到产品: {product.product_name}")
            
            # 3. 尝试从上游API获取完整的代理信息
            print("🔄 尝试从上游API获取完整代理信息...")
            
            try:
                # 使用上游ID查询代理信息
                static_proxy_service = StaticProxyService()
                
                # 先获取产品信息来确定provider
                provider_mapping = {
                    1: "Viettel",
                    2: "FPT", 
                    3: "VNPT",
                    4: "US",
                    5: "DatacenterA",
                    6: "DatacenterB",
                    7: "DatacenterC"
                }
                
                provider = provider_mapping.get(product.provider, "Viettel")
                
                # 调用list_proxies获取特定代理信息
                proxy_list_result = await static_proxy_service.list_proxies(provider, str(proxy_order.upstream_id))
                
                print(f"✅ 从上游API获取到响应: {proxy_list_result}")
                
                # 解析响应获取代理信息
                proxy_info = None
                if isinstance(proxy_list_result, list) and len(proxy_list_result) > 0:
                    # 如果返回的是列表，取第一个元素
                    proxy_info = proxy_list_result[0]
                elif isinstance(proxy_list_result, dict):
                    # 如果返回的是字典，直接使用
                    proxy_info = proxy_list_result
                
                if proxy_info:
                    print(f"✅ 解析到代理信息: {proxy_info}")
                    
                    # 4. 解析proxy字段获取连接信息
                    if 'proxy' in proxy_info and isinstance(proxy_info['proxy'], str):
                        proxy_string = proxy_info['proxy']
                        # 格式: ip:port:user:password
                        parts = proxy_string.split(':')
                        if len(parts) >= 4:
                            proxy_info['proxy_ip'] = parts[0]
                            proxy_info['port'] = int(parts[1])
                            proxy_info['user'] = parts[2]
                            proxy_info['password'] = parts[3]
                            print(f"✅ 解析代理连接信息: ip={parts[0]}, port={parts[1]}, user={parts[2]}")
                    
                    # 5. 更新订单的代理信息
                    # 保留现有的状态和时间信息，添加缺失的连接信息
                    current_info = proxy_order.proxy_info.copy() if proxy_order.proxy_info else {}
                    
                    # 合并代理信息，上游API的信息优先
                    updated_info = {**current_info, **proxy_info}
                    
                    proxy_order.proxy_info = updated_info
                    await db.commit()
                    
                    print(f"✅ 代理信息更新成功")
                    print(f"   更新后的完整信息: {updated_info}")
                    
                    # 6. 验证关键字段
                    key_fields = ['idproxy', 'ip', 'port', 'user', 'password']
                    missing_fields = []
                    for field in key_fields:
                        if field not in updated_info or updated_info[field] is None:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        print(f"⚠️  仍缺失字段: {missing_fields}")
                    else:
                        print("✅ 所有关键字段都已补全")
                        
                else:
                    print("❌ 上游API未返回有效的代理信息")
                    
            except Exception as e:
                print(f"❌ 调用上游API失败: {e}")
                logger.exception("上游API调用异常")
                
        except Exception as e:
            print(f"❌ 修复过程出错: {e}")
            logger.exception("修复过程异常")

async def check_all_static_orders():
    """检查所有静态代理订单的代理信息完整性"""
    print("\n🔍 检查所有静态代理订单...")
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ProxyOrder).where(
                ProxyOrder.order_id.like("STATIC_%"),
                ProxyOrder.status == "active"
            )
        )
        orders = result.scalars().all()
        
        print(f"找到 {len(orders)} 个活跃的静态代理订单")
        
        incomplete_orders = []
        for order in orders:
            if not order.proxy_info or not isinstance(order.proxy_info, dict):
                incomplete_orders.append(order.order_id)
                continue
                
            key_fields = ['idproxy', 'ip', 'port', 'user', 'password']
            missing_fields = []
            for field in key_fields:
                if field not in order.proxy_info or order.proxy_info[field] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                incomplete_orders.append({
                    'order_id': order.order_id,
                    'missing_fields': missing_fields
                })
        
        if incomplete_orders:
            print(f"❌ 发现 {len(incomplete_orders)} 个订单信息不完整:")
            for item in incomplete_orders:
                if isinstance(item, dict):
                    print(f"   {item['order_id']}: 缺失 {item['missing_fields']}")
                else:
                    print(f"   {item}: 代理信息为空")
        else:
            print("✅ 所有静态代理订单信息都完整")

async def main():
    """主函数"""
    print("🚀 开始修复缺失的代理信息...")
    print("=" * 60)
    
    await fix_missing_proxy_info()
    await check_all_static_orders()
    
    print("\n" + "=" * 60)
    print("🏁 修复完成")

if __name__ == "__main__":
    asyncio.run(main())
