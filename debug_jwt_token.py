import requests
import json
import jwt
from app.core.config import settings

BASE_URL = "http://localhost:8000"

def debug_jwt_token():
    """调试JWT token"""
    print("=== 调试JWT Token ===\n")
    
    # 1. 登录获取token
    print("1. 登录获取token...")
    login_response = requests.post(f"{BASE_URL}/api/v1/session/login", 
                                json={"username": "demo", "password": "demo123"})
    
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.status_code}")
        return False
    
    login_data = login_response.json()
    token = login_data.get('token') or login_data.get('access_token')
    print(f"✅ 登录成功，token: {token}")
    print(f"   Token长度: {len(token)}")
    
    # 2. 手动验证token
    print("\n2. 手动验证token...")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        print(f"✅ Token验证成功")
        print(f"   Payload: {payload}")
        print(f"   用户名: {payload.get('sub')}")
        print(f"   过期时间: {payload.get('exp')}")
    except Exception as e:
        print(f"❌ Token验证失败: {e}")
        return False
    
    # 3. 测试token在API中的使用
    print("\n3. 测试token在API中的使用...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试不需要认证的端点
    print("   3.1 测试不需要认证的端点...")
    response = requests.get(f"{BASE_URL}/api/v1/proxy/products", headers=headers)
    print(f"       状态码: {response.status_code}")
    
    # 测试需要认证的端点
    print("   3.2 测试需要认证的端点...")
    response = requests.get(f"{BASE_URL}/api/v1/proxy/list", headers=headers)
    print(f"       状态码: {response.status_code}")
    if response.status_code != 200:
        print(f"       响应: {response.text}")
    
    # 4. 检查请求头
    print("\n4. 检查请求头...")
    print(f"   Authorization header: {headers['Authorization']}")
    print(f"   Header格式正确: {headers['Authorization'].startswith('Bearer ')}")
    
    return True

if __name__ == "__main__":
    debug_jwt_token()
