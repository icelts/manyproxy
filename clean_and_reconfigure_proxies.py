#!/usr/bin/env python3
"""
清理所有现有供应商和产品数据，重新配置topproxy.vn映射关系
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import os

async def clean_all_data():
    """清理所有现有的供应商和产品数据"""
    print("🧹 开始清理所有现有数据...")

    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        # 1. 登录管理员账户获取 token
        print("\n1. 管理员登录...")
        login_data = {"username": "admin", "password": "admin123"}
        async with session.post(f"{base_url}/api/v1/session/login", json=login_data) as resp:
            if resp.status != 200:
                print(f"❌ 管理员登录失败: {resp.status}")
                return False
            token = (await resp.json()).get("token")
            print("✅ 管理员登录成功")

        headers = {"Authorization": f"Bearer {token}"}

        # 2. 删除所有产品映射
        print("\n2. 删除所有产品映射...")
        async with session.get(f"{base_url}/api/v1/admin/product-mappings", headers=headers) as resp:
            if resp.status == 200:
                mappings = await resp.json()
                for mapping in mappings:
                    async with session.delete(f"{base_url}/api/v1/admin/product-mappings/{mapping['id']}", headers=headers) as del_resp:
                        if del_resp.status == 200:
                            print(f"✅ 删除映射: {mapping['id']}")
                        else:
                            print(f"⚠️ 删除映射失败: {mapping['id']} ({del_resp.status})")
                print(f"📊 共处理 {len(mappings)} 个映射")

        # 3. 删除所有代理产品
        print("\n3. 删除所有代理产品...")
        async with session.get(f"{base_url}/api/v1/admin/proxy-products", headers=headers) as resp:
            if resp.status == 200:
                products = await resp.json()
                for product in products:
                    async with session.delete(f"{base_url}/api/v1/admin/proxy-products/{product['id']}", headers=headers) as del_resp:
                        if del_resp.status == 200:
                            print(f"✅ 删除产品: {product['product_name']}")
                        else:
                            print(f"⚠️ 删除产品失败: {product['product_name']} ({del_resp.status})")
                print(f"📊 共处理 {len(products)} 个产品")

        # 4. 删除所有上游供应商
        print("\n4. 删除所有上游供应商...")
        async with session.get(f"{base_url}/api/v1/admin/upstream-providers", headers=headers) as resp:
            if resp.status == 200:
                providers = await resp.json()
                for provider in providers:
                    async with session.delete(f"{base_url}/api/v1/admin/upstream-providers/{provider['id']}", headers=headers) as del_resp:
                        if del_resp.status == 200:
                            print(f"✅ 删除供应商: {provider['name']}")
                        else:
                            print(f"⚠️ 删除供应商失败: {provider['name']} ({del_resp.status})")
                print(f"📊 共处理 {len(providers)} 个供应商")

    print("\n🎉 数据清理完成！")
    return True

async def create_topproxy_products():
    """创建topproxy.vn的产品配置"""
    print("\n🏗️ 开始创建topproxy.vn产品配置...")

    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        # 1. 登录管理员账户获取 token
        login_data = {"username": "admin", "password": "admin123"}
        async with session.post(f"{base_url}/api/v1/session/login", json=login_data) as resp:
            if resp.status != 200:
                print(f"❌ 管理员登录失败: {resp.status}")
                return False
            token = (await resp.json()).get("token")

        headers = {"Authorization": f"Bearer {token}"}

        # 2. 创建TopProxy供应商
        print("\n2. 创建TopProxy供应商...")
        top_proxy_provider = {
            "name": "topproxy_vn",
            "display_name": "TopProxy.vn",
            "api_type": "static",
            "base_url": "https://topproxy.vn/apiv2",
            "api_key_param": "key",
            "api_key_value": os.getenv("TOPPROXY_KEY", ""),
            "config": {
                "timeout": 30,
                "retry": 3,
                "supported_endpoints": [
                    "muaproxy.php",
                    "doiproxy.php", 
                    "doibaomat.php",
                    "giahanproxy.php",
                    "listproxy.php"
                ],
                "supported_providers": [
                    "Viettel", "FPT", "VNPT", "US",
                    "DatacenterA", "DatacenterB", "DatacenterC",
                    "GoiViettel", "GoiVNPT", "GoiDATACENTER"
                ]
            },
            "is_active": True
        }

        async with session.post(f"{base_url}/api/v1/admin/upstream-providers", json=top_proxy_provider, headers=headers) as resp:
            if resp.status == 200:
                provider_id = (await resp.json()).get("id")
                print(f"✅ 创建TopProxy供应商成功 (ID: {provider_id})")
            else:
                print(f"❌ 创建TopProxy供应商失败: {await resp.text()}")
                return False

        # 3. 创建代理产品
        print("\n3. 创建代理产品...")
        
        # 产品配置 - 基于topproxy.vn的代理类型
        products_config = [
            # 越南家庭静态代理
            {
                "category": "static",
                "subcategory": "vietnam_home",
                "provider": "Viettel",
                "product_name": "Viettel Static Proxy",
                "description": "越南Viettel家庭静态代理 - 高质量住宅IP",
                "price": 50.00,
                "duration_days": 30,
                "stock": 100
            },
            {
                "category": "static", 
                "subcategory": "vietnam_home",
                "provider": "FPT",
                "product_name": "FPT Static Proxy",
                "description": "越南FPT家庭静态代理 - 稳定住宅IP",
                "price": 45.00,
                "duration_days": 30,
                "stock": 100
            },
            {
                "category": "static",
                "subcategory": "vietnam_home", 
                "provider": "VNPT",
                "product_name": "VNPT Static Proxy",
                "description": "越南VNPT家庭静态代理 - 企业级住宅IP",
                "price": 55.00,
                "duration_days": 30,
                "stock": 100
            },
            # 美国机房静态代理
            {
                "category": "static",
                "subcategory": "us_datacenter",
                "provider": "US",
                "product_name": "US Datacenter Proxy",
                "description": "美国机房静态代理 - 高速数据中心IP",
                "price": 30.00,
                "duration_days": 30,
                "stock": 200
            },
            # 越南机房静态代理
            {
                "category": "static",
                "subcategory": "vn_datacenter",
                "provider": "DatacenterA",
                "product_name": "Vietnam Datacenter A",
                "description": "越南机房静态代理A - 数据中心IP",
                "price": 25.00,
                "duration_days": 30,
                "stock": 150
            },
            {
                "category": "static",
                "subcategory": "vn_datacenter",
                "provider": "DatacenterB", 
                "product_name": "Vietnam Datacenter B",
                "description": "越南机房静态代理B - 数据中心IP",
                "price": 25.00,
                "duration_days": 30,
                "stock": 150
            },
            {
                "category": "static",
                "subcategory": "vn_datacenter",
                "provider": "DatacenterC",
                "product_name": "Vietnam Datacenter C", 
                "description": "越南机房静态代理C - 数据中心IP",
                "price": 25.00,
                "duration_days": 30,
                "stock": 150
            },
            # 套餐产品
            {
                "category": "static",
                "subcategory": "vietnam_home_package",
                "provider": "GoiViettel",
                "product_name": "Viettel Home Package",
                "description": "越南家庭静态代理套餐 - Viettel多IP套餐",
                "price": 200.00,
                "duration_days": 30,
                "stock": 50
            },
            {
                "category": "static",
                "subcategory": "vn_datacenter_package",
                "provider": "GoiVNPT",
                "product_name": "VNPT Datacenter Package",
                "description": "越南机房静态代理套餐 - VNPT多IP套餐",
                "price": 180.00,
                "duration_days": 30,
                "stock": 50
            },
            {
                "category": "static",
                "subcategory": "datacenter_package",
                "provider": "GoiDATACENTER",
                "product_name": "Datacenter Package",
                "description": "机房静态代理套餐 - 多数据中心IP套餐",
                "price": 150.00,
                "duration_days": 30,
                "stock": 50
            }
        ]

        created_products = {}
        for product_config in products_config:
            async with session.post(f"{base_url}/api/v1/admin/proxy-products", json=product_config, headers=headers) as resp:
                if resp.status == 200:
                    product = await resp.json()
                    created_products[product_config["provider"]] = product["id"]
                    print(f"✅ 创建产品成功: {product_config['product_name']} (ID: {product['id']})")
                else:
                    print(f"❌ 创建产品失败: {product_config['product_name']} ({await resp.text()})")

        # 4. 创建产品映射关系
        print("\n4. 创建产品映射关系...")
        
        for provider, product_id in created_products.items():
            mapping = {
                "product_id": product_id,
                "provider_id": provider_id,
                "upstream_product_code": provider,
                "price_multiplier": 1.0,
                "upstream_params": {
                    "loaiproxy": provider,
                    "type": "HTTP",
                    "quantity": 1,
                    "days": 30
                },
                "is_active": True
            }

            async with session.post(f"{base_url}/api/v1/admin/product-mappings", json=mapping, headers=headers) as resp:
                if resp.status == 200:
                    print(f"✅ 创建映射成功: {provider} → {provider}")
                else:
                    print(f"❌ 创建映射失败: {provider} ({await resp.text()})")

    print("\n🎉 TopProxy.vn产品配置完成！")
    return True

async def main():
    """主函数"""
    print("🚀 开始清理和重新配置代理系统...")
    print("=" * 60)
    
    # 1. 清理现有数据
    if not await clean_all_data():
        print("❌ 数据清理失败")
        return False
    
    print("\n" + "=" * 60)
    
    # 2. 创建新的配置
    if not await create_topproxy_products():
        print("❌ 产品配置失败")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 代理系统重新配置完成！")
    print("✅ 所有现有数据已清理")
    print("✅ TopProxy.vn供应商已创建")
    print("✅ 代理产品已创建")
    print("✅ 映射关系已建立")
    print("\n📋 支持的代理类型:")
    print("  • Viettel (越南家庭静态代理)")
    print("  • FPT (越南家庭静态代理)")
    print("  • VNPT (越南家庭静态代理)")
    print("  • US (美国机房静态代理)")
    print("  • DatacenterA/B/C (越南机房静态代理)")
    print("  • GoiViettel (越南家庭静态代理套餐)")
    print("  • GoiVNPT (越南机房静态代理套餐)")
    print("  • GoiDATACENTER (机房静态代理套餐)")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
