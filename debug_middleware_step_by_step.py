import requests
import json

BASE_URL = "http://localhost:8000"

def debug_middleware_step_by_step():
    """逐步调试中间件"""
    print("=== 逐步调试中间件 ===\n")
    
    # 1. 登录获取token
    print("1. 登录获取token...")
    login_response = requests.post(f"{BASE_URL}/api/v1/session/login", 
                                json={"username": "demo", "password": "demo123"})
    
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.status_code}")
        return False
    
    login_data = login_response.json()
    token = login_data.get('token') or login_data.get('access_token')
    print(f"✅ 登录成功，token: {token[:50]}...")
    
    # 2. 测试不同端点的认证行为
    print("\n2. 测试不同端点的认证行为...")
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoints = [
        ("/api/v1/session/api-keys", "Session API Keys"),
        ("/api/v1/proxy/products", "Proxy Products"),
        ("/api/v1/proxy/list", "Proxy List"),
    ]
    
    for endpoint, description in endpoints:
        print(f"\n   测试 {description} ({endpoint}):")
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        print(f"       状态码: {response.status_code}")
        if response.status_code != 200:
            print(f"       响应: {response.text}")
    
    # 3. 检查路径匹配
    print("\n3. 检查路径匹配...")
    protected_paths = ["/api/v1/proxy"]
    test_paths = [
        "/api/v1/session/api-keys",
        "/api/v1/proxy/products", 
        "/api/v1/proxy/list",
    ]
    
    for path in test_paths:
        is_protected = any(path.startswith(prefix) for prefix in protected_paths)
        print(f"   {path}: {'受保护' if is_protected else '不受保护'}")
    
    return True

if __name__ == "__main__":
    debug_middleware_step_by_step()
