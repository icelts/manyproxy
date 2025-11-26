#!/usr/bin/env python3
"""
调试API Key认证问题
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def debug_api_key_auth():
    """调试API Key认证"""
    print("=== 调试API Key认证 ===")
    
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
    
    # 2. 测试不同的API端点
    headers = {"X-API-Key": api_key}
    
    test_endpoints = [
        ("/api/v1/proxy/products", "GET", "产品列表"),
        ("/api/v1/proxy/stats", "GET", "代理统计"),
        ("/api/v1/proxy/list", "GET", "代理列表"),
        ("/api/v1/proxy/dynamic/123", "GET", "动态代理"),
    ]
    
    print("\n2. 测试API端点...")
    for endpoint, method, description in test_endpoints:
        print(f"\n   测试 {description} ({method} {endpoint})...")
        
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", headers=headers)
            
            print(f"   状态码: {response.status_code}")
            print(f"   响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                print(f"   ✅ {description} 成功")
                if endpoint == "/api/v1/proxy/products":
                    data = response.json()
                    print(f"   产品数量: {len(data)}")
            elif response.status_code == 401:
                print(f"   ❌ {description} 认证失败")
                print(f"   错误: {response.text}")
            elif response.status_code == 403:
                print(f"   ❌ {description} 权限不足")
                print(f"   错误: {response.text}")
            elif response.status_code == 404:
                print(f"   ⚠️  {description} 资源不存在（正常）")
            else:
                print(f"   ⚠️  {description} 其他状态码: {response.status_code}")
                print(f"   响应: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ❌ {description} 请求失败: {e}")
    
    # 3. 测试没有API Key的情况
    print("\n3. 测试没有API Key的情况...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/proxy/stats")
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    print("\n=== 调试完成 ===")
    return True

if __name__ == "__main__":
    debug_api_key_auth()
