#!/usr/bin/env python3
"""
调试中间件路径匹配问题
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_middleware_path_matching():
    """测试中间件路径匹配"""
    print("=== 调试中间件路径匹配 ===")
    
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
            print(f"   ✅ 获取API Key成功: {api_key[:20] if api_key else 'None'}...")
        else:
            print(f"   ❌ 登录失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 登录请求失败: {e}")
        return False
    
    if not api_key:
        print("   ❌ 没有获取到API Key")
        return False
    
    headers = {"X-API-Key": api_key}
    
    # 2. 测试不同路径的API Key认证
    test_paths = [
        "/api/v1/proxy/products",
        "/api/v1/proxy/stats", 
        "/api/v1/proxy/list",
        "/api/v1/proxy/static/buy",
        "/api/v1/proxy/dynamic/123",
        "/api/v1/proxy/mobile/123/reset",
    ]
    
    print("\n2. 测试不同路径的API Key认证...")
    for path in test_paths:
        print(f"\n   测试路径: {path}")
        
        # 检查路径是否以API_KEY_REQUIRED_PREFIXES开头
        API_KEY_REQUIRED_PREFIXES = ["/api/v1/proxy"]
        should_require_auth = any(path.startswith(prefix) for prefix in API_KEY_REQUIRED_PREFIXES)
        print(f"   需要认证: {should_require_auth}")
        
        # 检查是否在跳过列表中（使用修复后的模式）
        skip_auth_patterns = [
            "/api/v1/session/login",
            "/api/v1/session/register",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/",
            "/frontend/",
            "/css/",
            "/js/",
            "/pages/",
        ]
        
        should_skip = False
        for pattern in skip_auth_patterns:
            if pattern.endswith('/'):
                if path.startswith(pattern):
                    should_skip = True
                    break
            else:
                if path == pattern:
                    should_skip = True
                    break
        
        print(f"   跳过认证: {should_skip}")
        
        # 实际测试
        try:
            response = requests.get(f"{BASE_URL}{path}", headers=headers)
            print(f"   实际状态码: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ 成功")
            elif response.status_code == 401:
                print(f"   ❌ 认证失败")
            elif response.status_code == 404:
                print(f"   ⚠️  路径不存在")
            elif response.status_code == 405:
                print(f"   ⚠️  方法不允许（可能需要POST）")
            else:
                print(f"   ⚠️  其他状态码: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
    
    # 3. 测试POST请求
    print("\n3. 测试POST请求...")
    post_paths = [
        ("/api/v1/proxy/static/buy", {"provider": "default", "quantity": 1}),
        ("/api/v1/proxy/dynamic/buy", {"package_type": "basic", "quantity": 1}),
    ]
    
    for path, data in post_paths:
        print(f"\n   测试POST: {path}")
        try:
            response = requests.post(f"{BASE_URL}{path}", json=data, headers=headers)
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ 成功")
            elif response.status_code == 401:
                print(f"   ❌ 认证失败")
                print(f"   错误: {response.text}")
            elif response.status_code == 400:
                print(f"   ✅ 认证成功，业务逻辑错误（正常）")
            else:
                print(f"   ⚠️  其他状态码: {response.status_code}")
                print(f"   响应: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
    
    print("\n=== 中间件路径匹配调试完成 ===")
    return True

if __name__ == "__main__":
    test_middleware_path_matching()
