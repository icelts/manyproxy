#!/usr/bin/env python3
"""
详细调试中间件行为
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def debug_middleware():
    """调试中间件行为"""
    print("=== 详细调试中间件行为 ===")
    
    # 1. 先登录获取API Key
    print("\n1. 登录获取API Key...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/session/login", json=login_data)
        if response.status_code == 200:
            login_result = response.json()
            api_key = login_result.get('api_key')
            print(f"   ✅ 获取API Key成功: {api_key}")
        else:
            print(f"   ❌ 登录失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 登录请求失败: {e}")
        return False
    
    # 2. 测试不同的API端点，包括详细的请求信息
    headers = {"X-API-Key": api_key}
    
    test_endpoints = [
        "/api/v1/proxy/products",
        "/api/v1/proxy/stats", 
        "/api/v1/proxy/list",
        "/api/v1/proxy/dynamic/123",
        "/api/v1/proxy/static/buy",
        "/api/v1/proxy/dynamic/buy",
    ]
    
    print("\n2. 测试API端点...")
    for endpoint in test_endpoints:
        print(f"\n   测试端点: {endpoint}")
        
        # 测试GET请求
        print(f"   GET {endpoint}")
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            print(f"     状态码: {response.status_code}")
            if response.status_code == 401:
                print(f"     错误: {response.text}")
            elif response.status_code == 405:
                print(f"     方法不允许（可能需要POST）")
            elif response.status_code == 200:
                print(f"     ✅ 成功")
        except Exception as e:
            print(f"     ❌ 请求失败: {e}")
        
        # 如果是购买相关的端点，也测试POST
        if "buy" in endpoint:
            print(f"   POST {endpoint}")
            try:
                response = requests.post(f"{BASE_URL}{endpoint}", 
                                      json={"provider": "default", "quantity": 1},
                                      headers=headers)
                print(f"     状态码: {response.status_code}")
                if response.status_code == 401:
                    print(f"     错误: {response.text}")
                elif response.status_code == 200:
                    print(f"     ✅ 成功")
                elif response.status_code == 400:
                    print(f"     ✅ 认证成功，但业务逻辑错误（正常）")
            except Exception as e:
                print(f"     ❌ 请求失败: {e}")
    
    # 3. 测试路径匹配逻辑
    print("\n3. 测试路径匹配逻辑...")
    test_paths = [
        "/api/v1/proxy/products",
        "/api/v1/proxy/stats",
        "/api/v1/proxy/list",
        "/api/v1/proxy/dynamic/123",
        "/api/v1/session/login",
        "/api/v1/session/state",
    ]
    
    API_KEY_REQUIRED_PREFIXES = ["/api/v1/proxy"]
    
    for path in test_paths:
        should_auth = any(path.startswith(prefix) for prefix in API_KEY_REQUIRED_PREFIXES)
        print(f"   {path} -> 需要认证: {should_auth}")
    
    print("\n=== 调试完成 ===")
    return True

if __name__ == "__main__":
    debug_middleware()
