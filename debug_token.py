#!/usr/bin/env python3
"""
调试JWT token问题
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.security import create_access_token, verify_token
from app.core.config import settings

print(f"当前SECRET_KEY: {settings.SECRET_KEY}")
print(f"当前ALGORITHM: {settings.ALGORITHM}")

# 创建一个测试token
test_data = {"sub": "admin", "is_admin": True}
token = create_access_token(test_data)
print(f"生成的token: {token}")

# 立即验证
payload = verify_token(token)
print(f"验证结果: {payload}")

# 模拟重启后（重新生成SECRET_KEY）
print("\n模拟重启服务器...")
old_key = settings.SECRET_KEY
settings.SECRET_KEY = "new_secret_key_for_testing"
print(f"新的SECRET_KEY: {settings.SECRET_KEY}")

# 用新密钥验证旧token
payload = verify_token(token)
print(f"用新密钥验证旧token: {payload}")

# 用新密钥创建新token
new_token = create_access_token(test_data)
print(f"用新密钥生成的新token: {new_token}")

# 验证新token
payload = verify_token(new_token)
print(f"验证新token: {payload}")
