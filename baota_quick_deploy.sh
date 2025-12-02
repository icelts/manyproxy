#!/bin/bash
# 宝塔面板快速部署脚本

echo "=== 宝塔面板快速部署脚本 ==="
echo "此脚本将帮助您快速配置manyem项目"
echo ""

# 检查是否在正确的目录
if [ ! -f "app/main.py" ]; then
    echo "错误: 请在项目根目录下运行此脚本"
    exit 1
fi

# 设置环境变量
echo "1. 设置环境变量..."
export $(cat .env.production | xargs)

# 检查Python环境
echo "2. 检查Python环境..."
python3 --version
if [ $? -ne 0 ]; then
    echo "错误: Python3 未安装"
    exit 1
fi

# 安装依赖
echo "3. 安装Python依赖..."
pip3 install -r requirements.txt

# 运行数据库迁移
echo "4. 运行数据库迁移..."
alembic upgrade head

# 启动应用
echo "5. 启动应用..."
echo "应用将在后台运行，端口8000"
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 > app.log 2>&1 &

echo "应用已启动！"
echo "请访问: http://your-domain.com"
echo "查看日志: tail -f app.log"
echo ""
echo "=== 重要提醒 ==="
echo "1. 请确保宝塔面板的Nginx已正确配置反向代理"
echo "2. 请确保防火墙已开放8000端口"
echo "3. 请确保MySQL数据库可正常连接"
echo "4. 如果Redis不可用，应用会继续运行但缓存功能会被禁用"
