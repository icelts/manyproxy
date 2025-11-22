import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.security import verify_token, create_access_token

# 测试JWT令牌
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlcjIiLCJleHAiOjE3NTk0NzU0MTN9.UL9JxdLgDGGrVs3X1usJRL9PBkuo8yyO5yIVBZxHy7xk"

print("测试JWT令牌验证...")
print(f"令牌: {token}")

payload = verify_token(token)
print(f"验证结果: {payload}")

# 创建新令牌测试
print("\n创建新令牌测试...")
new_token = create_access_token(data={"sub": "testuser2"})
print(f"新令牌: {new_token}")

new_payload = verify_token(new_token)
print(f"新令牌验证结果: {new_payload}")
