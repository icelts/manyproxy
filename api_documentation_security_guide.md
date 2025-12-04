# API文档安全配置指南

## 概述

本文档说明了对项目进行的API文档安全配置修改，目的是屏蔽不必要的API接口，只向客户展示IP更换相关的核心接口。

## 修改内容

### 1. 创建公共API路由文件

**文件**: `app/api/v1/public_api.py`

创建了专门的公共API路由，只包含以下IP更换相关的接口：

- `POST /api/v1/mobile/{order_id}/reset` - 重置移动代理IP
- `POST /api/v1/mobile/token/{token}/reset` - 通过token重置移动代理IP
- `GET /api/v1/dynamic/{order_id}` - 获取动态代理IP
- `GET /api/v1/dynamic/token/{token}` - 通过token获取动态代理IP
- `POST /api/v1/static/{order_id}/change` - 更换静态代理类型
- `POST /api/v1/static/{order_id}/change-security` - 更改代理安全信息
- `GET /api/v1/info` - API服务信息

### 2. 修改主应用配置

**文件**: `app/main.py`

#### 主要修改：

1. **创建独立的公共API应用实例**：
   ```python
   public_app = FastAPI(
       title="IP更换接口服务",
       version="1.0.0",
       description="提供代理IP更换服务的API接口 - 客户专用文档",
       openapi_url="/public/openapi.json",
       docs_url="/public/docs",
       redoc_url="/public/redoc",
   )
   ```

2. **挂载公共API应用**：
   ```python
   app.mount("/public", public_app)
   ```

3. **更新认证中间件**：
   - 添加了公共API文档路径到跳过认证列表
   - 确保`/public/docs`、`/public/redoc`、`/public/openapi.json`等路径可以正常访问

4. **添加中间件支持**：
   - 为公共API应用添加了CORS和TrustedHost中间件

### 3. 更新应用描述

将主应用的描述更新为"Proxy Platform API: IP更换接口服务"，突出核心功能。

## 访问地址

### 客户专用API文档
- **Swagger UI**: `http://localhost:8000/public/docs`
- **ReDoc**: `http://localhost:8000/public/redoc`
- **OpenAPI规范**: `http://localhost:8000/public/openapi.json`
- **API信息**: `http://localhost:8000/public/info`

### 管理员API文档（仅在DEBUG=True时显示）
- **Swagger UI**: `http://localhost:8000/api/v1/docs`
- **ReDoc**: `http://localhost:8000/api/v1/redoc`
- **OpenAPI规范**: `http://localhost:8000/api/v1/openapi.json`

### 其他接口
- **健康检查**: `http://localhost:8000/health`
- **主页**: `http://localhost:8000/`

## 安全特性

### 1. 接口隔离
- 客户只能看到IP更换相关的接口
- 管理员接口（用户管理、订单管理、支付管理等）被完全隐藏
- 购买接口、产品列表等商业敏感接口不对外暴露

### 2. 认证保护
- 所有IP更换接口仍然需要API Key认证
- 在请求头中需要添加`X-API-Key`
- 支持速率限制和用户状态检查

### 3. 文档访问控制
- 公共API文档始终可用，方便客户查看
- 私有API文档仅在DEBUG模式下显示
- 生产环境中自动隐藏内部接口文档

## 测试验证

### 自动化测试脚本

**文件**: `test_public_api.py`

提供了完整的测试脚本，验证以下功能：

1. 公共API信息接口
2. 公共API文档页面
3. 公共API OpenAPI规范
4. 私有API是否被隐藏
5. 健康检查接口

### 运行测试

```bash
# 启动应用
python run.py

# 在另一个终端运行测试
python test_public_api.py
```

## 部署注意事项

### 1. 环境变量配置

确保在生产环境中设置：
```bash
DEBUG=False
```

这将自动隐藏完整的API文档，只显示客户专用的IP更换接口。

### 2. 反向代理配置

如果使用Nginx等反向代理，确保正确路由：

```nginx
# 客户API文档
location /public/ {
    proxy_pass http://localhost:8000/public/;
}

# 健康检查
location /health {
    proxy_pass http://localhost:8000/health;
}

# API接口（需要认证）
location /api/v1/ {
    proxy_pass http://localhost:8000/api/v1/;
}
```

### 3. 防火墙规则

考虑添加防火墙规则，限制对管理接口的访问：

```bash
# 只允许内网IP访问完整API
iptables -A INPUT -p tcp --dport 8000 -s 192.168.0.0/16 -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 --dport 8000 -j DROP
```

## 客户使用指南

### 1. 获取API Key

客户需要通过正常渠道注册账户并获取API Key。

### 2. 访问文档

客户可以通过以下地址查看可用的IP更换接口：
`http://your-domain.com/public/docs`

### 3. 使用接口

所有接口都需要在请求头中包含API Key：
```http
X-API-Key: your-api-key-here
```

### 4. 示例请求

```bash
# 重置移动代理IP
curl -X POST "http://your-domain.com/public/api/v1/mobile/ORDER123/reset" \
     -H "X-API-Key: your-api-key"

# 获取动态代理IP
curl -X GET "http://your-domain.com/public/api/v1/dynamic/ORDER456?carrier=random&province=0" \
     -H "X-API-Key: your-api-key"
```

## 维护说明

### 1. 添加新的IP更换接口

如果需要添加新的IP更换接口，请：

1. 在`app/api/v1/public_api.py`中添加接口定义
2. 确保接口路径以`/api/v1/`开头
3. 添加适当的认证和权限检查

### 2. 修改现有接口

修改公共接口时，请确保：

1. 保持向后兼容性
2. 更新相应的文档字符串
3. 测试公共API文档是否正确显示

### 3. 安全审计

定期进行安全审计：

1. 检查是否有敏感接口意外暴露
2. 验证认证机制是否正常工作
3. 监控API使用日志，发现异常访问

## 总结

通过以上配置，我们成功实现了：

✅ **接口隔离**: 客户只能看到IP更换相关的接口
✅ **安全保护**: 所有接口都需要API Key认证
✅ **文档分离**: 客户文档和管理员文档完全分离
✅ **生产安全**: 生产环境自动隐藏内部接口
✅ **易于维护**: 清晰的代码结构和完整的测试覆盖

这样的配置既满足了客户的使用需求，又保护了系统的商业敏感信息，是一个安全可靠的API文档解决方案。
