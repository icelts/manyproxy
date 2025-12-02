# ManyProxy 远程开发快速开始

## 🚀 最快上手方案

### 方案选择建议：
- **新手推荐**：VS Code Remote SSH（图形界面，简单易用）
- **专业开发**：SSH + 命令行（高效灵活）
- **团队协作**：Git + 同步（版本控制，多人开发）
- **生产部署**：Docker（环境一致，易于部署）

---

## ⚡ 5分钟快速开始（VS Code Remote SSH）

### 1. 安装必要软件
```bash
# 本地安装VS Code和扩展
# 1. 下载安装VS Code: https://code.visualstudio.com/
# 2. 安装扩展：Remote - SSH, Python, Pylance
```

### 2. 配置SSH连接
```bash
# 在本地终端生成SSH密钥（如果没有）
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"

# 复制公钥到服务器
ssh-copy-id username@your-server-ip

# 测试连接
ssh username@your-server-ip
```

### 3. VS Code连接远程
1. 打开VS Code
2. `Ctrl+Shift+P` → 输入 "Remote-SSH: Connect to Host"
3. 输入 `username@your-server-ip`
4. 选择项目文件夹 `/path/to/manyproxy`

### 4. 启动开发服务器
```bash
# 在VS Code终端中运行
cd /path/to/manyproxy
python3 -m pip install -r requirements.txt
python3 run.py --reload --host 0.0.0.0 --port 8000
```

### 5. 访问应用
- 前端：`http://your-server-ip:8000/frontend/index.html`
- API文档：`http://your-server-ip:8000/docs`

---

## 🔧 命令行快速开始

### 1. 连接服务器
```bash
ssh username@your-server-ip
cd /path/to/manyproxy
```

### 2. 环境检查和安装
```bash
# 检查Python
python3 --version

# 安装依赖
pip3 install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置
```

### 3. 启动应用
```bash
# 开发模式启动
python3 run.py --reload --host 0.0.0.0 --port 8000

# 或后台运行
nohup python3 run.py --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

### 4. 开放端口（如果需要）
```bash
# 开放8000端口
sudo ufw allow 8000
# 或
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

---

## 🐳 Docker快速开始

### 1. 创建Docker文件
```bash
# 在项目根目录创建Dockerfile（内容见remote_development_guide.md）
# 创建docker-compose.yml（内容见remote_development_guide.md）
```

### 2. 启动容器
```bash
# 构建并启动
docker-compose up --build -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

---

## 🔍 常用调试命令

### 查看应用状态
```bash
# 检查进程
ps aux | grep python

# 检查端口
netstat -tlnp | grep 8000

# 查看日志
tail -f logs/app.log
```

### 数据库操作
```bash
# 连接数据库
mysql -u username -p -h localhost manyproxy

# 查看用户
SELECT username, email, is_admin FROM users;
```

### API测试
```bash
# 测试登录
curl -X POST "http://localhost:8000/api/v1/session/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

---

## 🚨 常见问题快速解决

### 问题1：端口被占用
```bash
# 查找占用端口的进程
sudo lsof -i :8000

# 杀死进程
sudo kill -9 PID
```

### 问题2：依赖安装失败
```bash
# 更新pip
pip3 install --upgrade pip

# 清除缓存重装
pip3 cache purge
pip3 install -r requirements.txt --no-cache-dir
```

### 问题3：数据库连接失败
```bash
# 检查MySQL服务
sudo systemctl status mysql

# 重启MySQL
sudo systemctl restart mysql

# 检查配置
cat .env | grep DATABASE_URL
```

### 问题4：权限问题
```bash
# 修改文件权限
chmod +x run.py
chmod -R 755 frontend/

# 修改所有者
sudo chown -R username:username /path/to/manyproxy
```

---

## 📱 移动端访问

### 手机调试
```bash
# 确保绑定到0.0.0.0
python3 run.py --host 0.0.0.0 --port 8000

# 手机浏览器访问
http://your-server-ip:8000/frontend/index.html
```

### 内网穿透（临时测试）
```bash
# 使用ngrok（需要安装）
ngrok http 8000

# 或使用其他内网穿透工具
# 得到公网地址后即可在手机访问
```

---

## 🎯 下一步

1. **选择方案**：根据你的技能水平选择合适的远程开发方案
2. **环境配置**：按照对应方案配置开发环境
3. **开始开发**：启动应用，开始远程开发
4. **学习调试**：掌握常用的调试技巧
5. **安全设置**：配置SSH密钥和防火墙规则

---

## 📞 需要帮助？

- 查看完整指南：`remote_development_guide.md`
- 检查项目文档：`README.md`
- 查看部署指南：`deployment_guide.md`

**开始你的远程开发之旅吧！** 🚀
