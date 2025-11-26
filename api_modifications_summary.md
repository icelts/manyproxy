# API修改总结

## 修改概述

根据用户要求，对代理产品系统进行了以下两个主要修改：

1. **移除固定时长限制**：所有代理产品现在只有一个时长，由管理员在添加产品时设置，之前的30、60、90天等固定时长已弃用
2. **简化认证机制**：所有代理产品购买和管理API现在只需要API Key认证，不再支持JWT认证或用户ID查询

## 详细修改内容

### 1. 产品时长问题修复

#### 修改的文件：
- `app/schemas/proxy.py`
- `app/services/proxy_service.py`
- `app/api/v1/endpoints/proxy.py`

#### 具体修改：

**1.1 Schema修改 (`app/schemas/proxy.py`)**
- 移除了 `ProxyProductUpdate` 中的 `duration_options` 字段
- 移除了 `StaticProxyPurchase` 中的 `duration_days` 字段的 `Literal` 限制

**1.2 服务层修改 (`app/services/proxy_service.py`)**
- 修改了 `_get_static_unit_price` 方法，现在直接使用产品的固定价格
- 移除了 `buy_static_proxy` 方法中的固定时长检查
- 移除了 `change_proxy_security` 方法中的固定时长检查
- 价格计算现在基于产品设置的 `duration_days`，不再限制为固定值

**1.3 API端点修改 (`app/api/v1/endpoints/proxy.py`)**
- 修改了 `renew_static_proxy` 端点，将 `days` 参数从 `Literal[30, 60, 90]` 改为 `int`（最小值为1）
- 现在支持任意天数的续费

### 2. 认证机制简化

#### 修改的文件：
- `app/main.py`
- `app/api/v1/endpoints/proxy.py`

#### 具体修改：

**2.1 中间件修改 (`app/main.py`)**
- 移除了JWT认证逻辑
- 现在只支持API Key认证
- 如果没有提供API Key，直接返回401错误
- 保留了API Key的速率限制功能

**2.2 API端点注释更新 (`app/api/v1/endpoints/proxy.py`)**
- 更新了 `get_current_api_user` 函数的注释，明确说明仅支持API Key认证
- 更新了错误消息，从 "Authentication required" 改为 "API key required"

## 影响的API端点

所有 `/api/v1/proxy/*` 下的端点现在都只支持API Key认证：

### 购买相关端点：
- `POST /api/v1/proxy/static/buy` - 购买静态代理
- `POST /api/v1/proxy/dynamic/buy` - 购买动态代理
- `POST /api/v1/proxy/mobile/buy` - 购买移动代理

### 管理相关端点：
- `GET /api/v1/proxy/list` - 获取用户代理列表
- `GET /api/v1/proxy/stats` - 获取代理统计信息
- `POST /api/v1/proxy/static/{order_id}/change` - 更换静态代理类型
- `POST /api/v1/proxy/static/{order_id}/change-security` - 更改代理安全信息
- `POST /api/v1/proxy/static/{order_id}/renew` - 续费静态代理
- `GET /api/v1/proxy/static/upstream-list` - 获取上游代理列表

### 查询相关端点：
- `GET /api/v1/proxy/products` - 获取产品列表
- `GET /api/v1/proxy/dynamic/{order_id}` - 获取动态代理
- `GET /api/v1/proxy/dynamic/token/{token}` - 通过token获取动态代理
- `POST /api/v1/proxy/mobile/{order_id}/reset` - 重置移动代理IP
- `POST /api/v1/proxy/mobile/token/{token}/reset` - 通过token重置移动代理IP
- `GET /api/v1/proxy/static/providers` - 获取支持的代理类型

## 使用方式

### API认证
所有代理相关API现在需要在请求头中包含：
```
X-API-Key: your_api_key_here
```

### 产品时长
- 产品现在只有一个固定的时长，由管理员在创建产品时设置
- 续费可以指定任意天数（最小1天）
- 不再限制为30、60、90天等固定值

## 测试

创建了测试脚本 `test_api_changes.py` 来验证修改：

1. **测试无API Key访问**：应该返回401错误
2. **测试JWT认证禁用**：应该返回401错误
3. **测试API Key认证**：应该正常访问（需要有效的API Key）

运行测试：
```bash
python test_api_changes.py
```

## 注意事项

1. **向后兼容性**：现有的API Key继续有效，但JWT token不再被接受
2. **产品数据**：现有产品的 `duration_options` 字段可能需要清理
3. **前端更新**：如果前端有使用JWT认证的地方，需要更新为使用API Key
4. **文档更新**：API文档需要更新以反映新的认证要求

## 总结

这些修改简化了系统的认证机制，使其更适合API集成的使用场景，同时提供了更灵活的产品时长配置。用户现在可以通过简单的API Key调用来购买和管理代理产品，而无需处理复杂的JWT认证流程。
