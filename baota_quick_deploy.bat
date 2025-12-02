@echo off
REM 宝塔面板快速部署脚本 (Windows版本)

echo === 宝塔面板快速部署脚本 (Windows版本) ===
echo 此脚本将帮助您快速配置manyem项目
echo.

REM 检查是否在正确的目录
if not exist "app\main.py" (
    echo 错误: 请在项目根目录下运行此脚本
    pause
    exit /b 1
)

REM 检查Python环境
echo 1. 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: Python 未安装或未添加到PATH
    pause
    exit /b 1
)

REM 安装依赖
echo 2. 安装Python依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 警告: 依赖安装可能失败，请检查pip配置
)

REM 运行数据库迁移
echo 3. 运行数据库迁移...
alembic upgrade head
if %errorlevel% neq 0 (
    echo 警告: 数据库迁移可能失败，请检查数据库连接
)

REM 启动应用
echo 4. 启动应用...
echo 应用将在后台运行，端口8000
start /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

echo 应用已启动！
echo 请访问: http://your-domain.com
echo 查看日志: type app.log
echo.
echo === 重要提醒 ===
echo 1. 请确保宝塔面板的Nginx已正确配置反向代理
echo 2. 请确保防火墙已开放8000端口
echo 3. 请确保MySQL数据库可正常连接
echo 4. 如果Redis不可用，应用会继续运行但缓存功能会被禁用
echo.
pause
