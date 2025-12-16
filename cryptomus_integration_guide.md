# Cryptomus支付网关集成指南

本指南详细说明如何在ManyProxy项目中集成和使用Cryptomus加密货币支付网关。

## 📋 目录

1. [概述](#概述)
2. [功能特性](#功能特性)
3. [配置步骤](#配置步骤)
4. [API接口](#api接口)
5. [前端集成](#前端集成)
6. [测试验证](#测试验证)
7. [部署说明](#部署说明)
8. [故障排除](#故障排除)

## 🚀 概述

Cryptomus是一个专业的加密货币支付网关，支持多种主流加密货币的收款和付款。通过集成Cryptomus，您的ManyProxy项目将支持：

- ✅ 真实的加密货币支付处理
- ✅ 多币种支持（BTC、ETH、USDT、USDC等）
- ✅ 实时汇率转换
- ✅ 安全的签名验证
- ✅ 自动化支付状态跟踪
- ✅ Webhook回调处理

## ✨ 功能特性

### 🔐 安全特性
- **HMAC-SHA256签名验证** - 确保所有通信安全
- **Webhook签名验证** - 防止恶意回调
- **IP白名单** - 可限制API访问IP（可选）
- **令牌验证** - 多层安全保护

### 💰 支付功能
- **多币种支持** - BTC、ETH、USDT、USDC、TRX、LTC、DASH
- **实时汇率** - 自动获取最新汇率
- **灵活支付** - 支持一次性支付和多次支付
- **静态钱包** - 可创建固定的收款地址

### 🔄 容错机制
- **模拟回退** - 当Cryptomus不可用时自动回退到模拟模式
- **错误重试** - 自动重试失败请求
- **状态缓存** - 本地缓存支付状态提高性能

## ⚙️ 配置步骤

### 1. 获取Cryptomus账户

1. 访问 [Cryptomus官网](https://cryptomus.com)
2. 注册商户账户
3. 完成身份验证（KYC）
4. 获取API密钥和商户UUID

### 2. 环境变量配置

在项目根目录的 `.env` 文件中添加以下配置：

```bash
# Cryptomus支付网关配置
CRYPTOMUS_API_KEY=your_payment_api_key_here
CRYPTOMUS_PAYOUT_KEY=your_payout_api_key_here
CRYPTOMUS_MERCHANT_UUID=your_merchant_uuid_here
CRYPTOMUS_BASE_URL=https://api.cryptomus.com/v1
CRYPTOMUS_WEBHOOK_URL=https://your-domain.com/api/v1/orders/payments/cryptomus-webhook

# 支付回调安全令牌
PAYMENT_CALLBACK_TOKEN=your_secure_callback_token_here
```

### 3. 依赖安装

```bash
# 安装新的依赖
pip install -r requirements.txt

# 或者手动安装aiohttp
pip install aiohttp==3.9.1
```

### 4. 数据库迁移

```bash
# 运行数据库迁移（如果添加了新字段）
alembic upgrade head
```

## 🔌 API接口

### 新增端点

#### 1. Cryptomus Webhook
```
POST /api/v1/orders/payments/cryptomus-webhook
```

**功能**: 接收Cryptomus的支付状态通知
**安全**: HMAC签名验证
**格式**: JSON

#### 2. 账户余额查询
```
GET /api/v1/orders/crypto/balance
```

**功能**: 查询Cryptomus账户余额
**权限**: 需要管理员权限

#### 3. 支持的加密货币
```
GET /api/v1/orders/crypto/currencies
```

**功能**: 获取支持的加密货币列表
**返回**: 包含汇率、限制、佣金等信息

### 现有端点增强

所有现有的支付相关端点都已经增强以支持Cryptomus：

- `POST /api/v1/orders/recharge` - 创建Cryptomus支付
- `GET /api/v1/orders/payments/{payment_id}` - 获取支付状态
- `GET /api/v1/orders/payments/{payment_id}/monitor` - 实时监控
- `GET /api/v1/orders/payments/{payment_id}/qrcode` - 生成二维码

## 🎨 前端集成

### 1. 充值页面更新

充值页面 (`frontend/pages/recharge.html`) 已经支持：

- ✅ 动态加载支持的加密货币
- ✅ 实时汇率显示
- ✅ Cryptomus支付链接
- ✅ 二维码生成和显示
- ✅ 支付状态实时监控

### 2. 支付流程

1. **选择金额** - 用户选择充值金额
2. **选择货币** - 从Cryptomus支持的货币中选择
3. **创建支付** - 调用后端API创建Cryptomus支付
4. **扫码支付** - 显示二维码或支付链接
5. **状态监控** - 前端轮询检查支付状态
6. **完成充值** - 支付确认后自动到账

### 3. 用户体验优化

- **自动刷新** - 支付状态自动刷新
- **倒计时** - 显示支付剩余时间
- **确认数显示** - 实时显示区块链确认数
- **错误处理** - 友好的错误提示和重试

## 🧪 测试验证

### 1. 运行集成测试

```bash
# 运行完整集成测试
python test_cryptomus_integration.py
```

测试内容包括：
- ✅ 配置文件检查
- ✅ 数据库模型验证
- ✅ Cryptomus客户端连接
- ✅ 加密支付服务功能
- ✅ API端点响应

### 2. 手动测试流程

1. **启动服务**
   ```bash
   python run.py
   ```

2. **访问充值页面**
   ```
   http://localhost:8000/frontend/pages/recharge.html
   ```

3. **测试支付流程**
   - 选择测试金额（如$10）
   - 选择USDT或其他支持的货币
   - 点击"立即充值"
   - 扫描二维码或访问支付链接
   - 验证支付状态更新

### 3. Webhook测试

```bash
# 使用ngrok等工具暴露本地端口
ngrok http 8000

# 在Cryptomus后台设置webhook URL
# 格式: https://your-ngrok-url.ngrok.io/api/v1/orders/payments/cryptomus-webhook
```

## 🚀 部署说明

### 1. 生产环境配置

```bash
# 设置生产环境变量
export CRYPTOMUS_API_KEY="prod_api_key"
export CRYPTOMUS_MERCHANT_UUID="prod_merchant_uuid"
export CRYPTOMUS_WEBHOOK_URL="https://your-domain.com/api/v1/orders/payments/cryptomus-webhook"
export PAYMENT_CALLBACK_TOKEN="secure_prod_token"

# 使用生产配置启动
export ENVIRONMENT=production
python run.py
```

### 2. 反向代理设置

如果使用Nginx等反向代理，确保：

```nginx
location /api/v1/orders/payments/cryptomus-webhook {
    proxy_pass http://localhost:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 3. SSL证书

确保生产环境使用HTTPS：
- Cryptomus要求webhook URL使用HTTPS
- 前端页面也建议使用HTTPS

### 4. 监控和日志

设置日志监控：
```python
# 日志级别
import logging
logging.basicConfig(level=logging.INFO)

# 关键操作日志
logger.info("Cryptomus payment created: {payment_id}")
logger.error("Cryptomus API error: {error}")
```

## 🔧 故障排除

### 常见问题

#### 1. 配置问题
**问题**: `Cryptomus not configured` 错误
**解决**: 检查环境变量是否正确设置
```bash
echo $CRYPTOMUS_API_KEY
echo $CRYPTOMUS_MERCHANT_UUID
```

#### 2. 签名验证失败
**问题**: `Invalid signature` 错误
**解决**: 
- 检查API密钥是否正确
- 确认webhook数据格式
- 验证时间戳是否在有效范围内

#### 3. 支付创建失败
**问题**: `Cryptomus payment creation failed` 错误
**解决**:
- 检查API密钥权限
- 验证商户UUID
- 确认网络参数正确

#### 4. Webhook未收到
**问题**: 支付成功但未收到回调
**解决**:
- 检查webhook URL是否可访问
- 确认防火墙设置
- 验证SSL证书

### 调试工具

#### 1. 启用调试模式
```python
# 在config.py中设置
DEBUG = True
```

#### 2. 查看详细日志
```bash
# 启动时显示详细日志
python run.py --log-level DEBUG
```

#### 3. 手动测试API
```bash
# 使用curl测试webhook
curl -X POST \
  -H "Content-Type: application/json" \
  -H "sign: your_signature" \
  -d '{"uuid":"test","payment_status":"paid"}' \
  https://your-domain.com/api/v1/orders/payments/cryptomus-webhook
```

## 📊 性能优化

### 1. 缓存策略
- **支付状态缓存** - 减少API调用
- **汇率缓存** - 定时更新汇率
- **服务列表缓存** - 缓存支持的货币

### 2. 异步处理
- **异步API调用** - 使用aiohttp异步请求
- **并发处理** - 支持多个并发支付
- **超时控制** - 防止长时间等待

### 3. 监控指标
- **成功率监控** - 跟踪支付成功率
- **响应时间** - 监控API响应时间
- **错误率** - 跟踪错误率和类型

## 🔐 安全建议

### 1. API密钥管理
- 使用环境变量存储密钥
- 定期轮换API密钥
- 限制API密钥权限范围

### 2. Webhook安全
- 验证所有webhook请求
- 使用HTTPS传输
- 实施IP白名单

### 3. 数据保护
- 加密敏感数据传输
- 记录详细的审计日志
- 定期备份数据

## 📞 技术支持

### Cryptomus支持
- **官方文档**: https://doc.cryptomus.com
- **技术支持**: support@cryptomus.com
- **API状态**: https://status.cryptomus.com

### 项目支持
- **GitHub Issues**: 在项目仓库提交问题
- **文档更新**: 查看最新文档和更新
- **社区支持**: 参与社区讨论

---

## 🎉 部署检查清单

部署前请确认以下项目：

- [ ] Cryptomus账户已创建并通过KYC
- [ ] API密钥和商户UUID已获取
- [ ] 环境变量已正确配置
- [ ] 依赖已安装并测试通过
- [ ] 数据库迁移已完成
- [ ] Webhook URL可访问并使用HTTPS
- [ ] 集成测试全部通过
- [ ] 生产环境安全检查完成
- [ ] 监控和日志已配置
- [ ] 备份策略已制定

完成以上项目后，您的ManyProxy项目就成功集成了Cryptomus支付网关！🚀
