// 主应用模块
class App {
    constructor() {
        this.currentPage = 'login';
        this.init();
    }

    async init() {
        // 初始化事件监听器
        this.initEventListeners();
        
        // 初始化API密钥管理
        this.initApiKeyManagement();
        
        // 等待DOM加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.onDOMReady();
            });
        } else {
            this.onDOMReady();
        }
    }

    initEventListeners() {
        console.log('初始化事件监听器...');
        
        // 导航链接
        document.querySelectorAll('[data-page]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('导航链接被点击:', e.target.getAttribute('data-page'));
                const page = e.target.getAttribute('data-page');
                this.showPage(page);
            });
        });

        // 页面切换事件
        window.addEventListener('popstate', (e) => {
            console.log('popstate事件触发:', e.state);
            if (e.state && e.state.page) {
                this.showPage(e.state.page, false);
            }
        });
    }

    initApiKeyManagement() {
        // 创建API密钥表单
        document.getElementById('create-api-key-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleCreateApiKey();
        });

        // 确认创建API密钥
        document.getElementById('confirm-create-api-key').addEventListener('click', () => {
            this.handleCreateApiKey();
        });
    }

    onDOMReady() {
        console.log('应用已初始化');
        
        // 确保所有页面元素都已加载
        setTimeout(() => {
            // 检查认证状态，但不强制跳转
            // 让认证管理器自己处理页面跳转逻辑
            console.log('应用初始化完成，认证状态检查由认证管理器处理');
            
            // 调试：检查页面元素是否存在
            console.log('登录页面元素:', document.getElementById('login-page'));
            console.log('仪表板页面元素:', document.getElementById('dashboard-page'));
            console.log('认证状态:', sessionController.isAuthenticated());
        }, 100);
    }

    showPage(pageName, addToHistory = true) {
        console.log('显示页面:', pageName);
        
        // 隐藏所有页面
        document.querySelectorAll('.page').forEach(page => {
            console.log('隐藏页面:', page.id);
            page.style.display = 'none';
        });

        // 显示目标页面
        const targetPage = document.getElementById(`${pageName}-page`);
        if (targetPage) {
            console.log('找到目标页面元素:', targetPage);
            console.log('设置页面显示为block');
            targetPage.style.display = 'block';
            this.currentPage = pageName;

            // 更新导航栏激活状态
            this.updateNavigation(pageName);

            // 页面特定的初始化
            this.initPage(pageName);

            // 更新浏览器历史
            if (addToHistory) {
                history.pushState({ page: pageName }, '', `#${pageName}`);
            }
            
            // 强制重绘以确保页面显示
            targetPage.offsetHeight;
            
            // 再次确认页面显示状态
            console.log('页面显示状态检查:', targetPage.style.display);
        } else {
            console.error('找不到页面元素:', `${pageName}-page`);
        }
    }

    updateNavigation(activePage) {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });

        const activeLink = document.querySelector(`[data-page="${activePage}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
    }

    async initPage(pageName) {
        switch (pageName) {
            case 'dashboard':
                await this.initDashboard();
                break;
            case 'proxy':
                await this.initProxyPage();
                break;
            case 'api-keys':
                await this.initApiKeysPage();
                break;
        }
    }

    async initDashboard() {
        // 加载仪表板数据
        await dashboardManager.loadDashboardData();
        dashboardManager.updateApiCallStats();
    }

    async initProxyPage() {
        // 加载代理列表
        await proxyManager.loadProxyList();
        
        // 加载当前活跃标签页的数据
        const activeTab = document.querySelector('.nav-tabs .nav-link.active');
        if (activeTab) {
            activeTab.dispatchEvent(new Event('shown.bs.tab'));
        }
    }

    async initApiKeysPage() {
        // 加载API密钥列表
        await this.loadApiKeys();
    }

    async handleCreateApiKey() {
        const name = document.getElementById('api-key-name').value;
        const rateLimit = parseInt(document.getElementById('api-key-rate-limit').value);
        
        if (!name) {
            this.showToast('请输入API密钥名称', 'warning');
            return;
        }

        const confirmBtn = document.getElementById('confirm-create-api-key');
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="loading"></span> 创建中...';

        try {
            const result = await api.createApiKey(name, rateLimit);
            
            this.showToast('API密钥创建成功！', 'success');
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('createApiKeyModal'));
            modal.hide();
            
            // 重置表单
            document.getElementById('create-api-key-form').reset();
            
            // 刷新API密钥列表
            await this.loadApiKeys();
            
            // 显示新创建的API密钥
            this.showNewApiKey(result);
            sessionController.updateApiKey(result.api_key);
            
        } catch (error) {
            console.error('创建API密钥失败:', error);
            this.showToast(error.message || '创建API密钥失败', 'error');
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '创建';
        }
    }

    async loadApiKeys() {
        try {
            const apiKeys = await api.getApiKeys();
            this.syncApiKeyState(apiKeys);
            this.renderApiKeys(apiKeys);
        } catch (error) {
            console.error('加载API密钥失败:', error);
            document.getElementById('api-keys-list').innerHTML = 
                '<tr><td colspan="6" class="text-center text-muted">加载API密钥失败</td></tr>';
        }
    }

    renderApiKeys(apiKeys) {
        const container = document.getElementById('api-keys-list');
        
        if (!apiKeys || apiKeys.length === 0) {
            container.innerHTML = '<tr><td colspan="6" class="text-center text-muted">暂无API密钥</td></tr>';
            return;
        }

        container.innerHTML = apiKeys.map(key => `
            <tr>
                <td>${key.name}</td>
                <td>
                    <div class="code-block">${this.maskApiKey(key.api_key)}</div>
                    <button class="btn btn-sm btn-outline-secondary mt-1" onclick="app.copyApiKey('${key.api_key}')">
                        <i class="fas fa-copy"></i> 复制
                    </button>
                </td>
                <td>${key.rate_limit || 1000}/小时</td>
                <td>
                    <span class="badge ${key.is_active ? 'bg-success' : 'bg-danger'}">
                        ${key.is_active ? '活跃' : '已禁用'}
                    </span>
                </td>
                <td>${this.formatDate(key.created_at)}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-warning" onclick="app.rotateApiKey(${key.id})">
                            <i class="fas fa-sync"></i> 轮换
                        </button>
                        <button class="btn btn-outline-danger" onclick="app.deleteApiKey(${key.id})">
                            <i class="fas fa-trash"></i> 删除
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    syncApiKeyState(apiKeys) {
        const activeKey = (apiKeys || []).find(key => key.is_active) || apiKeys?.[0];
        if (activeKey?.api_key) {
            sessionController.updateApiKey(activeKey.api_key);
        } else {
            sessionController.updateApiKey(null);
        }
    }

    maskApiKey(apiKey) {
        if (!apiKey) return '';
        return apiKey.substring(0, 8) + '****' + apiKey.substring(apiKey.length - 4);
    }

    async rotateApiKey(keyId) {
        if (!confirm('确定要轮换这个API密钥吗？轮换后旧密钥将失效。')) {
            return;
        }

        try {
            const result = await api.rotateApiKey(keyId);
            this.showToast('API密钥已轮换', 'success');
            await this.loadApiKeys();
            this.showNewApiKey(result);
            sessionController.updateApiKey(result.api_key);
        } catch (error) {
            console.error('轮换API密钥失败:', error);
            this.showToast(error.message || '轮换失败', 'error');
        }
    }

    async deleteApiKey(keyId) {
        if (!confirm('确定要删除这个API密钥吗？此操作不可撤销。')) {
            return;
        }

        try {
            await api.deleteApiKey(keyId);
            this.showToast('API密钥已删除', 'success');
            await this.loadApiKeys();
        } catch (error) {
            console.error('删除API密钥失败:', error);
            this.showToast(error.message || '删除失败', 'error');
        }
    }

    copyApiKey(apiKey) {
        navigator.clipboard.writeText(apiKey).then(() => {
            this.showToast('API密钥已复制到剪贴板', 'success');
        }).catch(() => {
            this.showToast('复制失败，请手动复制', 'error');
        });
    }

    showNewApiKey(apiKeyData) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">API密钥创建成功</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>您的API密钥已创建，请妥善保管：</p>
                        <div class="code-block">${apiKeyData.api_key}</div>
                        <div class="alert alert-warning mt-3">
                            <i class="fas fa-exclamation-triangle"></i>
                            请立即复制并保存此密钥，出于安全考虑，我们不会再次显示完整密钥。
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" onclick="app.copyApiKey('${apiKeyData.api_key}')">
                            <i class="fas fa-copy"></i> 复制密钥
                        </button>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');
        
        toastMessage.textContent = message;
        
        // 设置toast样式
        toast.className = 'toast';
        // 清除所有现有的背景类
        toast.classList.remove('bg-success', 'bg-danger', 'bg-warning', 'bg-info', 'text-white', 'text-dark');
        
        switch (type) {
            case 'success':
                toast.classList.add('bg-success', 'text-white');
                break;
            case 'error':
                toast.classList.add('bg-danger', 'text-white');
                break;
            case 'warning':
                toast.classList.add('bg-warning', 'text-dark');
                break;
            default:
                toast.classList.add('bg-info', 'text-white');
        }
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // 增加API调用计数
        dashboardManager.incrementApiCallCount();
    }

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    // 获取当前页面
    getCurrentPage() {
        return this.currentPage;
    }

    // 检查用户权限
    checkPermission(permission) {
        // 这里可以添加权限检查逻辑
        return true;
    }
}

// 创建全局应用实例
const app = new App();

// 导出应用实例
window.app = app;
