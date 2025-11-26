#!/usr/bin/env python3
"""
调试路径匹配逻辑
"""

def test_path_matching():
    """测试路径匹配逻辑"""
    print("=== 测试路径匹配逻辑 ===")
    
    API_KEY_REQUIRED_PREFIXES = [
        "/api/v1/proxy",
    ]
    
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
    
    test_paths = [
        "/api/v1/proxy/products",
        "/api/v1/proxy/stats",
        "/api/v1/proxy/list",
        "/api/v1/session/login",
        "/api/v1/session/state",
        "/",
        "/frontend/index.html",
    ]
    
    for path in test_paths:
        print(f"\n测试路径: {path}")
        
        # 检查是否应该跳过认证
        should_skip = False
        for pattern in skip_auth_patterns:
            if pattern == '/':
                # Special case: root path should only match exactly
                if path == pattern:
                    should_skip = True
                    print(f"  匹配跳过模式: {pattern} (根路径精确匹配)")
                    break
            elif pattern.endswith('/'):
                # Directory prefix match
                if path.startswith(pattern):
                    should_skip = True
                    print(f"  匹配跳过模式: {pattern} (前缀匹配)")
                    break
            else:
                # Exact match
                if path == pattern:
                    should_skip = True
                    print(f"  匹配跳过模式: {pattern} (精确匹配)")
                    break
        
        if should_skip:
            print(f"  结果: 跳过认证")
            continue
        
        # 检查是否在需要认证的前缀下
        should_auth = any(path.startswith(prefix) for prefix in API_KEY_REQUIRED_PREFIXES)
        print(f"  需要认证: {should_auth}")
        
        if should_auth:
            print(f"  结果: 需要API Key认证")
        else:
            print(f"  结果: 不需要认证")

if __name__ == "__main__":
    test_path_matching()
