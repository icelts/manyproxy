#!/usr/bin/env python3
"""
初始化真实的代理供应商和映射关系（集成 topProxy.vn API）
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import os

async def init_real_providers_and_mappings():
    """初始化 topProxy.vn 供应商和映射关系"""
    print("🚀 初始化 topProxy.vn 代理供应商和映射关系...")

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

        # 2. 创建 topProxy 供应商
        print("\n2. 创建 topProxy 供应商...")
        top_proxy_provider = {
            "name": "topproxy_vn",
            "display_name": "TopProxy.vn Provider",
            "api_type": "multi",
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
                ]
            },
            "is_active": True
        }

        async with session.post(f"{base_url}/api/v1/admin/upstream-providers", json=top_proxy_provider, headers=headers) as resp:
            if resp.status == 200:
                provider_id = (await resp.json()).get("id")
                print(f"✅ 创建 TopProxy 提供商成功 (ID: {provider_id})")
            elif resp.status == 400 and "already exists" in await resp.text():
                async with session.get(f"{base_url}/api/v1/admin/upstream-providers", headers=headers) as get_resp:
                    providers = await get_resp.json()
                    provider_id = next((p["id"] for p in providers if p["name"] == "topproxy_vn"), None)
                    print(f"ℹ️ 提供商已存在 (ID: {provider_id})")
            else:
                print(f"❌ 创建 TopProxy 提供商失败 ({await resp.text()})")
                return False

        # 3. 获取系统产品
        async with session.get(f"{base_url}/api/v1/admin/proxy-products", headers=headers) as resp:
            if resp.status != 200:
                print("❌ 获取产品列表失败")
                return False
            products = await resp.json()
            print(f"📦 获取到 {len(products)} 个产品")

        # 4. 映射关系（对应 topProxy.vn 的 loaiproxy）
        mapping_list = [
            ("Viettel Proxy", "Viettel"),
            ("FPT Proxy", "FPT"),
            ("VNPT Proxy", "VNPT"),
            ("US Datacenter Proxy", "US"),
            ("DatacenterA Proxy", "DatacenterA"),
            ("DatacenterB Proxy", "DatacenterB"),
            ("DatacenterC Proxy", "DatacenterC"),
            ("GoiViettel Proxy", "GoiViettel"),
            ("GoiVNPT Proxy", "GoiVNPT"),
            ("GoiDATACENTER Proxy", "GoiDATACENTER"),
        ]

        for product_name, loaiproxy in mapping_list:
            product_id = next((p["id"] for p in products if p["product_name"] == product_name), None)
            if not product_id:
                print(f"⚠️ 未找到产品: {product_name}")
                continue

            mapping = {
                "product_id": product_id,
                "provider_id": provider_id,
                "upstream_product_code": loaiproxy,
                "price_multiplier": 1.0,
                "upstream_params": {"loaiproxy": loaiproxy, "type": "HTTP"},
                "is_active": True
            }

            async with session.post(f"{base_url}/api/v1/admin/product-mappings", json=mapping, headers=headers) as resp:
                if resp.status == 200:
                    print(f"✅ 创建映射成功: {product_name} → loaiproxy={loaiproxy}")
                elif resp.status == 400 and "already exists" in await resp.text():
                    print(f"ℹ️ 映射已存在: {product_name} → loaiproxy={loaiproxy}")
                else:
                    print(f"❌ 创建映射失败 ({await resp.text()})")

    print("\n🎉 初始化完成！")
    print("✅ TopProxy.vn 映射关系已建立")
    return True

if __name__ == "__main__":
    success = asyncio.run(init_real_providers_and_mappings())
    exit(0 if success else 1)
