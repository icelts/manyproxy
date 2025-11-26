import requests
import json

BASE_URL = "http://localhost:8000"

def test_middleware_behavior():
    """测试中间件行为"""
    print("=== 测试中间件行为 ===\n")
    
    # 1. 登录获取token
    print("1. 登录获取token...")
    login_response = requests.post(f"{BASE_URL}/api/v1/session/login", 
                                json={"username": "demo", "password": "demo123"})
    
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.status_code}")
        return False
    
    login_data = login_response.json()
    token = login_data.get('token') or login_data.get('access_token')
    print(f"✅ 登录成功，token: {token[:20]}...")
    
    # 2. 创建API Key
    print("\n2. 创建API Key...")
    headers = {"Authorization": f"Bearer {token}"}
    api_key_response = requests.post(f"{BASE_URL}/api/v1/session/api-keys", 
                                   json={"name": "middleware-test-key"}, 
                                   headers=headers)
    
    if api_key_response.status_code != 200:
        print(f"❌ 创建API Key失败: {api_key_response.status_code} - {api_key_response.text}")
        return False
    
    api_key_data = api_key_response.json()
    api_key = api_key_data.get('api_key')
    print(f"✅ API Key创建成功: {api_key[:20]}...")
    
    # 3. 测试不同端点的认证行为
    print("\n3. 测试不同端点的认证行为...")
    
    test_endpoints = [
        ("GET", "/api/v1/proxy/products", "产品列表（无需认证）"),
        ("GET", "/api/v1/proxy/list", "代理列表（需要认证）"),
        ("POST", "/api/v1/proxy/static/buy", "购买静态代理（需要认证）"),
    ]
    
    for method, endpoint, description in test_endpoints:
        print(f"\n   测试 {description}:")
        
        # 3.1 无认证
        print(f"     无认证:")
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}")
        else:
            response = requests.post(f"{BASE_URL}{endpoint}", json={"product_id": 7, "quantity": 1})
        print(f"       状态码: {response.status_code}")
        if response.status_code != 200:
            print(f"       响应: {response.text}")
        
        # 3.2 JWT Token认证
        print(f"     JWT Token认证:")
        jwt_headers = {"Authorization": f"Bearer {token}"}
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", headers=jwt_headers)
        else:
            response = requests.post(f"{BASE_URL}{endpoint}", json={"product_id": 7, "quantity": 1}, headers=jwt_headers)
        print(f"       状态码: {response.status_code}")
        if response.status_code != 200:
            print(f"       响应: {response.text}")
        
        # 3.3 API Key认证
        print(f"     API Key认证:")
        api_headers = {"X-API-Key": api_key}
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", headers=api_headers)
        else:
            response = requests.post(f"{BASE_URL}{endpoint}", json={"product_id": 7, "quantity": 1}, headers=api_headers)
        print(f"       状态码: {response.status_code}")
        if response.status_code != 200:
            print(f"       响应: {response.text}")
    
    return True

if __name__ == "__main__":
    test_middleware_behavior()
