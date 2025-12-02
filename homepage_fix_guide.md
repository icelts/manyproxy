# 首页显示问题修复指南

## 问题描述
访问域名时显示 `{"message":"Proxy Platform API","version":"1.0.0"}` 而不是网站首页。

## 问题原因
FastAPI的根路径 `/` 默认返回API信息，而不是网站首页。

## 解决方案

### 1. 已修复的代码
我已经修改了 `app/main.py` 中的根路径处理：

```python
@app.get("/")
async def root():
    """Root endpoint - returns the homepage."""
    from fastapi.responses import FileResponse
    import os
    
    homepage_path = "frontend/index.html"
    if os.path.exists(homepage_path):
        return FileResponse(homepage_path)
    else:
        return {"message": "Proxy Platform API", "version": settings.VERSION}
```

### 2. 需要上传的文件
1. **修复文件**（之前的问题）：
   - `frontend/components/footer.js`
   - `.env`

2. **首页修复**：
   - `app/main.py` - 修改了根路径返回首页

3. **生产环境配置**：
   - `.env.production`

### 3. 部署步骤

#### 步骤1：上传修复文件
```bash
# 备份当前文件
cp app/main.py app/main.py.backup
cp .env .env.backup

# 上传新文件并覆盖
# - app/main.py
# - frontend/components/footer.js  
# - .env.production
```

#### 步骤2：配置生产环境
```bash
# 使用生产环境配置
cp .env.production .env

# 生成安全密钥（重要！）
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))"
python -c "import secrets; print('PAYMENT_CALLBACK_TOKEN=' + secrets.token_urlsafe(32))"

# 编辑.env文件，替换生成的密钥
nano .env
```

#### 步骤3：重启服务
```bash
# 重启应用
sudo systemctl restart your-app-service

# 确保Redis运行
sudo systemctl start redis
sudo systemctl enable redis
```

### 4. 验证修复

#### 测试首页
```bash
# 应该返回HTML内容，而不是JSON
curl "https://manyem.com/"

# 检查HTTP状态码
curl -I "https://manyem.com/"
# 应该返回 200 OK
```

#### 测试其他功能
```bash
# 测试footer组件
curl -I "https://manyem.com/components/footer.html"

# 测试登录API
curl -X POST "https://manyem.com/api/v1/session/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 5. Nginx配置优化

你的当前Nginx配置基本正确，但建议添加缓存优化：

```nginx
# 静态文件缓存
location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# HTML文件缓存
location ~* \.(html)$ {
    expires 1h;
    add_header Cache-Control "public";
}
```

### 6. 故障排除

#### 如果仍然显示API信息：
1. 检查文件是否正确上传：`ls -la app/main.py`
2. 检查应用日志：`tail -f logs/app.log`
3. 确认服务重启：`sudo systemctl status your-app-service`

#### 如果静态文件404：
1. 检查文件权限：`ls -la frontend/`
2. 检查Nginx配置中的路径映射
3. 确认静态文件目录存在

#### 如果登录失败：
1. 检查Redis状态：`sudo systemctl status redis`
2. 检查数据库连接
3. 查看.env配置是否正确

### 7. 完整的文件清单

需要上传/修改的文件：
- ✅ `app/main.py` - 修复首页显示
- ✅ `frontend/components/footer.js` - 修复footer路径
- ✅ `.env.production` - 生产环境配置
- ✅ `production_config_guide.md` - 配置指南
- ✅ `homepage_fix_guide.md` - 本修复指南

### 8. 预期结果

部署完成后：
- 访问 `https://manyem.com/` 显示网站首页
- Footer组件正常加载
- 登录功能正常工作
- 所有静态文件正确加载

如果还有问题，请检查应用日志和Nginx日志进行进一步排查。
