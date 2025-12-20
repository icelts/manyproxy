# 服务器部署命令清单

## 🚀 快速部署命令

### 1. 基础拉取和启动
```bash
# 进入项目目录
cd /path/to/manyproxy

# 拉取最新代码
git pull origin master

# 安装新依赖
pip install -r requirements.txt

# 启动服务
python run.py
```

### 2. 完整部署脚本（推荐）
```bash
# 下载并运行部署脚本
wget https://raw.githubusercontent.com/icelts/manyproxy/master/server_deploy_v2.0.0.sh
chmod +x server_deploy_v2.0.0.sh
./server_deploy_v2.0.0.sh
```

### 3. 手动完整部署
```bash
# 1. 进入项目目录
cd /path/to/manyproxy

# 2. 停止现有服务
pkill -f "python run.py"

# 3. 拉取最新代码
git pull origin master

# 4. 安装依赖
pip install -r requirements.txt

# 5. 检查环境变量
ls -la .env

# 6. 数据库迁移（如果需要）
alembic upgrade head

# 7. 启动服务
nohup python run.py > manyproxy.log 2>&1 &

# 8. 检查状态
ps aux | grep "python run.py"
```

## 🔧 配置检查

### 环境变量配置
```bash
# 检查.env文件是否存在
ls -la .env

# 如果不存在，从模板复制
cp .env.example .env

# 编辑配置文件
nano .env
```

**必需配置项：**
```bash
CRYPTOMUS_API_KEY=your_api_key_here
CRYPTOMUS_MERCHANT_UUID=your_merchant_uuid_here
CRYPTOMUS_WEBHOOK_URL=https://your-domain.com/api/v1/orders/payments/cryptomus-webhook
```

## 🧪 测试命令

### 1. API测试
```bash
# 测试支付API
python test_payment_api.py

# 测试Cryptomus集成
python test_cryptomus_ascii.py
```

### 2. 手动API测试
```bash
# 测试货币列表
curl http://localhost:8000/api/v1/orders/crypto/currencies

# 测试服务状态
curl http://localhost:8000/health
```

## 📊 服务管理

### 查看服务状态
```bash
# 查看进程
ps aux | grep "python run.py"

# 查看端口
netstat -tlnp | grep :8000

# 查看日志
tail -f manyproxy.log
```

### 停止服务
```bash
# 停止服务
pkill -f "python run.py"

# 强制停止
kill -9 $(pgrep -f "python run.py")
```

### 重启服务
```bash
# 重启服务
pkill -f "python run.py"
sleep 2
python run.py

# 后台重启
pkill -f "python run.py"
nohup python run.py > manyproxy.log 2>&1 &
```

## 🔍 故障排除

### 检查常见问题
```bash
# 1. 检查Python环境
python --version

# 2. 检查依赖
pip list | grep aiohttp

# 3. 检查配置
python -c "from app.core.config import settings; print('API Key:', bool(settings.CRYPTOMUS_API_KEY))"

# 4. 检查数据库
python -c "from app.core.database import engine; print('DB OK:', engine)"
```

### 查看错误日志
```bash
# 查看最近的错误
tail -50 manyproxy.log | grep ERROR

# 实时监控日志
tail -f manyproxy.log
```

## 🌐 访问地址

部署成功后的访问地址：
- **主页**: http://your-domain.com:8000
- **充值页面**: http://your-domain.com:8000/frontend/pages/recharge.html
- **管理后台**: http://your-domain.com:8000/frontend/pages/admin.html
- **API文档**: http://your-domain.com:8000/docs

## 📱 移动端测试

```bash
# 测试移动端访问
curl -A "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)" \
     http://localhost:8000/frontend/pages/recharge.html
```

## 🔒 安全检查

```bash
# 检查HTTPS配置
curl -I https://your-domain.com/api/v1/orders/crypto/currencies

# 检查防火墙
ufw status

# 检查SSL证书
openssl s_client -connect your-domain.com:443
```

---

## 📞 需要帮助？

如果遇到问题：
1. 查看 `manyproxy.log` 日志文件
2. 运行 `python test_cryptomus_ascii.py` 诊断
3. 检查环境变量配置
4. 确认网络连接正常

**快速诊断命令：**
```bash
python -c "
try:
    from app.services.cryptomus_client import get_cryptomus_client
    print('✅ Cryptomus客户端导入成功')
except Exception as e:
    print(f'❌ 导入失败: {e}')
"
