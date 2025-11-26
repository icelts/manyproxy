import requests
import json

BASE_URL = "http://localhost:8000"

def debug_simple():
    """简单调试"""
    print("=== 简单调试 ===\n")
    
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
    
    # 2. 创建API Key
    print("\n2. 创建API Key...")
    headers = {"Authorization": f"Bearer {token}"}
    api_key_response = requests.post(f"{BASE_URL}/api/v1/session/api-keys", 
                                   json={"name": "simple-test-key"}, 
                                   headers=headers)
    
    if api_key_response.status_code != 200:
        print(f"❌ 创建API Key失败: {api_key_response.status_code} - {api_key_response.text}")
        return False
    
    api_key_data = api_key_response.json()
    api_key = api_key_data.get('api_key')
    print(f"✅ API Key创建成功: {api_key[:50]}...")
    
    # 3. 测试不同的认证方式
    print("\n3. 测试认证...")
    
    # 测试JWT认证
    print("   3.1 JWT认证测试...")
    jwt_headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/proxy/list", headers=jwt_headers)
    print(f"       状态码: {response.status_code}")
    print(f"       响应: {response.text}")
    
    # 测试API Key认证
    print("   3.2 API Key认证测试...")
    api_headers = {"X-API-Key": api_key}
    response = requests.get(f"{BASE_URL}/api/v1/proxy/list", headers=api_headers)
    print(f"       状态码: {response.status_code}")
    print(f"       响应: {response.text}")
    
    return True

if __name__ == "__main__":
    debug_simple()
