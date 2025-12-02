# ManyProxy 远程开发与调试指南

## 🚀 远程开发方案概览

基于您的ManyProxy项目已上传到服务器，这里提供几种远程开发和调试的方案：

### 方案一：SSH + 远程开发（推荐）
### 方案二：Docker容器化开发
### 方案三：Git + 本地开发同步
### 方案四：VS Code Remote SSH扩展

---

## 📋 前置检查清单

<task_progress>
- [ ] 确认服务器基本信息（IP、用户名、SSH访问）
- [ ] 检查服务器环境（Python版本、数据库、Redis）
- [ ] 确认项目文件已正确上传
- [ ] 验证网络端口开放情况
- [ ] 配置SSH密钥认证
</task_progress>

---

## 🔧 方案一：SSH + 远程开发（推荐）

### 1. 服务器环境准备

```bash
# 连接到服务器
ssh username@your-server-ip

# 检查Python环境
python3 --version
pip3 --version

# 安装项目依赖
cd /path/to/manyproxy
pip3 install -r requirements.txt

# 检查数据库连接
mysql -u username -p -h localhost

# 检查Redis服务
redis-cli ping
```

### 2. 配置开发环境

```bash
# 创建开发环境配置
cp .env.example .env.development

# 编辑开发环境变量
nano .env.development
```

开发环境配置示例：
```env
# 数据库配置
DATABASE_URL=mysql+aiomysql://dev_user:dev_pass@localhost:3306/manyproxy_dev

# JWT配置
SECRET_KEY=your-dev-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 开发模式
DEBUG=true
LOG_LEVEL=debug
```

### 3. 启动开发服务器

```bash
# 方式1：使用项目启动脚本
python3 run.py --reload --host 0.0.0.0 --port 8000

# 方式2：直接使用uvicorn
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### 4. 防火墙和端口配置

```bash
# 开放8000端口（如果使用ufw）
sudo ufw allow 8000

# 或者使用iptables
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT

# 检查端口状态
sudo netstat -tlnp | grep 8000
```

---

## 🐳 方案二：Docker容器化开发

### 1. 创建Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. 创建docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+aiomysql://root:password@db:3306/manyproxy
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - .:/app
    command: python run.py --reload --host 0.0.0.0

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: manyproxy
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  mysql_data:
```

### 3. 启动Docker环境

```bash
# 构建并启动
docker-compose up --build

# 后台运行
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 进入容器调试
docker-compose exec app bash
```

---

## 🔄 方案三：Git + 本地开发同步

### 1. 设置Git工作流

```bash
# 在本地克隆项目
git clone https://github.com/icelts/manyproxy.git
cd manyproxy

# 创建开发分支
git checkout -b feature/remote-development

# 设置远程服务器为额外的remote
git remote add server username@your-server-ip:/path/to/manyproxy.git
```

### 2. 本地开发环境

```bash
# 安装本地依赖
pip install -r requirements.txt

# 配置本地环境变量
cp .env.example .env.local

# 启动本地开发服务器
python run.py --reload --port 8000
```

### 3. 同步到服务器

```bash
# 提交本地更改
git add .
git commit -m "Development changes"
git push origin feature/remote-development

# 推送到服务器
git push server feature/remote-development

# 在服务器上拉取更改
ssh username@your-server-ip
cd /path/to/manyproxy
git pull origin feature/remote-development

# 重启服务
sudo systemctl restart manyproxy
```

---

## 💻 方案四：VS Code Remote SSH扩展

### 1. 安装VS Code扩展

在本地VS Code中安装：
- Remote - SSH
- Python
- Pylance

### 2. 配置SSH连接

```bash
# 创建SSH配置文件
mkdir -p ~/.ssh
nano ~/.ssh/config
```

SSH配置示例：
```
Host manyproxy-server
    HostName your-server-ip
    User username
    Port 22
    IdentityFile ~/.ssh/id_rsa
    ForwardAgent yes
```

### 3. 连接到远程服务器

1. 打开VS Code
2. 按 `Ctrl+Shift+P`
3. 输入 "Remote-SSH: Connect to Host"
4. 选择 "manyproxy-server"
5. 选择项目文件夹 `/path/to/manyproxy`

### 4. 远程调试配置

在VS Code中创建 `.vscode/launch.json`：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/run.py",
            "args": ["--reload", "--host", "0.0.0.0", "--port", "8000"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

---

## 🐛 调试技巧和工具

### 1. 日志调试

```bash
# 实时查看应用日志
tail -f logs/app.log

# 查看特定服务的日志
journalctl -u manyproxy -f

# Docker日志
docker-compose logs -f app
```

### 2. 数据库调试

```bash
# 连接数据库
mysql -u username -p -h localhost manyproxy

# 查看用户表
SELECT * FROM users LIMIT 10;

# 查看代理表
SELECT * FROM proxies LIMIT 10;
```

### 3. API调试

```bash
# 测试登录API
curl -X POST "http://your-server-ip:8000/api/v1/session/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 测试代理API
curl -X GET "http://your-server-ip:8000/api/v1/proxy/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 4. 性能监控

```bash
# 安装监控工具
pip install py-spy

# 监控Python进程
py-spy top --pid $(pgrep -f "python.*run.py")

# 生成火焰图
py-spy record --pid $(pgrep -f "python.*run.py") -o profile.svg
```

---

## 🔒 安全注意事项

### 1. SSH安全

```bash
# 禁用密码认证，只使用密钥
sudo nano /etc/ssh/sshd_config
# 设置：PasswordAuthentication no

# 使用非标准端口
# Port 2222

# 限制SSH访问
sudo ufw allow from your-ip to any port 22
```

### 2. 应用安全

```bash
# 不要在生产环境暴露调试端口
# 只在开发环境使用 --reload

# 使用环境变量管理敏感信息
# 不要在代码中硬编码密码

# 定期更新依赖
pip install --upgrade -r requirements.txt
```

### 3. 网络安全

```bash
# 使用VPN或SSH隧道访问开发服务器
ssh -L 8000:localhost:8000 username@your-server-ip

# 配置防火墙规则
sudo ufw deny 8000  # 默认拒绝
sudo ufw allow from your-ip to any port 8000  # 只允许你的IP
```

---

## 📊 监控和维护

### 1. 系统监控脚本

创建 `monitor.sh`：
```bash
#!/bin/bash

echo "=== System Status ==="
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')"
echo "Memory: $(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2}')"
echo "Disk: $(df -h / | awk 'NR==2 {print $5}')"

echo "=== Application Status ==="
if pgrep -f "python.*run.py" > /dev/null; then
    echo "App: Running (PID: $(pgrep -f "python.*run.py"))"
else
    echo "App: Not Running"
fi

echo "=== Database Status ==="
if mysqladmin ping -h localhost --silent; then
    echo "Database: Connected"
else
    echo "Database: Disconnected"
fi

echo "=== Redis Status ==="
if redis-cli ping > /dev/null 2>&1; then
    echo "Redis: Connected"
else
    echo "Redis: Disconnected"
fi
```

### 2. 自动重启脚本

创建 `auto_restart.sh`：
```bash
#!/bin/bash

APP_PID=$(pgrep -f "python.*run.py")

if [ -z "$APP_PID" ]; then
    echo "Application is not running, restarting..."
    cd /path/to/manyproxy
    nohup python run.py --host 0.0.0.0 --port 8000 > logs/app.log 2>&1 &
    echo "Application restarted with PID: $!"
else
    echo "Application is running with PID: $APP_PID"
fi
```

### 3. 定时任务配置

```bash
# 编辑crontab
crontab -e

# 添加监控任务（每5分钟检查一次）
*/5 * * * * /path/to/manyproxy/auto_restart.sh

# 添加日志清理任务（每天凌晨2点）
0 2 * * * find /path/to/manyproxy/logs -name "*.log" -mtime +7 -delete
```

---

## 🚨 故障排除

### 常见问题和解决方案

#### 1. 应用无法启动
```bash
# 检查端口占用
sudo netstat -tlnp | grep 8000

# 检查Python环境
python3 -c "import fastapi; print('FastAPI OK')"

# 检查依赖
pip3 install -r requirements.txt --force-reinstall
```

#### 2. 数据库连接失败
```bash
# 测试数据库连接
mysql -u username -p -h localhost

# 检查数据库服务
sudo systemctl status mysql

# 查看数据库日志
sudo tail -f /var/log/mysql/error.log
```

#### 3. Redis连接问题
```bash
# 测试Redis连接
redis-cli ping

# 检查Redis服务
sudo systemctl status redis

# 重启Redis
sudo systemctl restart redis
```

#### 4. 前端静态文件404
```bash
# 检查文件权限
ls -la frontend/

# 检查Nginx配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

---

## 📞 获取帮助

### 日志位置
- 应用日志：`logs/app.log`
- 系统日志：`/var/log/syslog`
- Nginx日志：`/var/log/nginx/`
- MySQL日志：`/var/log/mysql/`

### 有用的命令
```bash
# 查看系统资源
htop
df -h
free -m

# 网络诊断
ping your-server-ip
traceroute your-server-ip
telnet your-server-ip 8000

# 进程管理
ps aux | grep python
kill -9 PID
```

---

## 🎯 推荐工作流

1. **开发阶段**：使用VS Code Remote SSH进行远程开发
2. **测试阶段**：在服务器上创建测试环境
3. **部署阶段**：使用Docker容器化部署
4. **监控阶段**：设置监控脚本和告警

选择适合您需求的方案，开始远程开发吧！
