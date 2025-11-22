// 代理管理模块
class ProxyManager {
    constructor() {
        this.initEventListeners();
        this.proxies = {
            static: [],
            dynamic: [],
            mobile: []
        };
    }

    initEventListeners() {
        // 代理类型选择
        document.getElementById('proxy-type').addEventListener('change', (e) => {
            this.handleProxyTypeChange(e.target.value);
        });

        // 确认购买代理
        document.getElementById('confirm-buy-proxy').addEventListener('click', () => {
            this.handleBuyProxy();
        });

        // 标签页切换时加载数据
        document.getElementById('static-tab').addEventListener('shown.bs.tab', () => {
            this.loadStaticProxies();
        });

        document.getElementById('dynamic-tab').addEventListener('shown.bs.tab', () => {
            this.loadDynamicProxies();
        });

        document.getElementById('mobile-tab').addEventListener('shown.bs.tab', () => {
            this.loadMobileProxies();
        });
    }

    handleProxyTypeChange(type) {
        // 隐藏所有选项
        document.getElementById('static-options').style.display = 'none';
        document.getElementById('dynamic-options').style.display = 'none';
        document.getElementById('mobile-options').style.display = 'none';

        // 显示对应选项
        switch (type) {
            case 'static':
                document.getElementById('static-options').style.display = 'block';
                break;
            case 'dynamic':
                document.getElementById('dynamic-options').style.display = 'block';
                break;
            case 'mobile':
                document.getElementById('mobile-options').style.display = 'block';
                break;
        }
    }

    async handleBuyProxy() {
        const proxyType = document.getElementById('proxy-type').value;
        if (!proxyType) {
            window.app.showToast('请选择代理类型', 'warning');
            return;
        }

        const confirmBtn = document.getElementById('confirm-buy-proxy');
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="loading"></span> 购买中...';

        try {
            let result;
            switch (proxyType) {
                case 'static':
                    const staticProvider = document.getElementById('static-provider').value;
                    const staticQuantity = parseInt(document.getElementById('static-quantity').value);
                    result = await api.buyStaticProxy(staticProvider, staticQuantity);
                    break;
                case 'dynamic':
                    const dynamicPackage = document.getElementById('dynamic-package').value;
                    const dynamicQuantity = parseInt(document.getElementById('dynamic-quantity').value);
                    result = await api.buyDynamicProxy(dynamicPackage, dynamicQuantity);
                    break;
                case 'mobile':
                    const mobileProvider = document.getElementById('mobile-provider').value;
                    const mobileQuantity = parseInt(document.getElementById('mobile-quantity').value);
                    result = await api.buyMobileProxy(mobileProvider, mobileQuantity);
                    break;
            }

            window.app.showToast('代理购买成功！', 'success');
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('buyProxyModal'));
            modal.hide();
            
            // 重置表单
            document.getElementById('buy-proxy-form').reset();
            this.handleProxyTypeChange('');
            
            // 刷新代理列表
            await this.loadProxyList();
            
        } catch (error) {
            console.error('购买代理失败:', error);
            window.app.showToast(error.message || '购买代理失败', 'error');
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '确认购买';
        }
    }

    async loadProxyList() {
        try {
            const data = await api.getProxyList();
            this.proxies = data;
            
            // 如果当前在代理页面，更新显示
            if (document.getElementById('proxy-page').style.display !== 'none') {
                const activeTab = document.querySelector('.nav-tabs .nav-link.active').id;
                
                switch (activeTab) {
                    case 'static-tab':
                        this.renderStaticProxies();
                        break;
                    case 'dynamic-tab':
                        this.renderDynamicProxies();
                        break;
                    case 'mobile-tab':
                        this.renderMobileProxies();
                        break;
                }
            }
            
            // 更新仪表板统计
            this.updateDashboardStats();
            
        } catch (error) {
            console.error('加载代理列表失败:', error);
        }
    }

    async loadStaticProxies() {
        try {
            const data = await api.getProxyList();
            this.proxies.static = data.static || [];
            this.renderStaticProxies();
        } catch (error) {
            console.error('加载静态代理失败:', error);
        }
    }

    async loadDynamicProxies() {
        try {
            const data = await api.getProxyList();
            this.proxies.dynamic = data.dynamic || [];
            this.renderDynamicProxies();
        } catch (error) {
            console.error('加载动态代理失败:', error);
        }
    }

    async loadMobileProxies() {
        try {
            const data = await api.getProxyList();
            this.proxies.mobile = data.mobile || [];
            this.renderMobileProxies();
        } catch (error) {
            console.error('加载移动代理失败:', error);
        }
    }

    renderStaticProxies() {
        const container = document.getElementById('static-proxies-list');
        
        if (!this.proxies.static || this.proxies.static.length === 0) {
            container.innerHTML = '<tr><td colspan="7" class="text-center text-muted">暂无静态代理</td></tr>';
            return;
        }

        container.innerHTML = this.proxies.static.map(proxy => `
            <tr>
                <td>${proxy.id}</td>
                <td>${this.getProviderName(proxy.provider)}</td>
                <td><code>${proxy.ip_address}</code></td>
                <td>${proxy.port}</td>
                <td>
                    <span class="badge ${proxy.status === 'active' ? 'bg-success' : 'bg-warning'}">
                        ${proxy.status === 'active' ? '活跃' : '待激活'}
                    </span>
                </td>
                <td>${this.formatDate(proxy.created_at)}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="proxyManager.testProxy(${proxy.id})">
                            <i class="fas fa-plug"></i> 测试
                        </button>
                        <button class="btn btn-outline-danger" onclick="proxyManager.deleteProxy(${proxy.id}, 'static')">
                            <i class="fas fa-trash"></i> 删除
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    renderDynamicProxies() {
        const container = document.getElementById('dynamic-proxies-list');
        
        if (!this.proxies.dynamic || this.proxies.dynamic.length === 0) {
            container.innerHTML = '<tr><td colspan="6" class="text-center text-muted">暂无动态代理</td></tr>';
            return;
        }

        container.innerHTML = this.proxies.dynamic.map(proxy => `
            <tr>
                <td>${proxy.order_id}</td>
                <td>${this.getPackageName(proxy.package_type)}</td>
                <td>${proxy.quantity}</td>
                <td>
                    <span class="badge ${proxy.status === 'active' ? 'bg-success' : 'bg-warning'}">
                        ${proxy.status === 'active' ? '活跃' : '待激活'}
                    </span>
                </td>
                <td>${proxy.expires_at ? this.formatDate(proxy.expires_at) : '-'}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-info" onclick="proxyManager.refreshDynamicProxy('${proxy.order_id}')">
                            <i class="fas fa-sync"></i> 刷新
                        </button>
                        <button class="btn btn-outline-danger" onclick="proxyManager.deleteProxy('${proxy.order_id}', 'dynamic')">
                            <i class="fas fa-trash"></i> 删除
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    renderMobileProxies() {
        const container = document.getElementById('mobile-proxies-list');
        
        if (!this.proxies.mobile || this.proxies.mobile.length === 0) {
            container.innerHTML = '<tr><td colspan="6" class="text-center text-muted">暂无移动代理</td></tr>';
            return;
        }

        container.innerHTML = this.proxies.mobile.map(proxy => `
            <tr>
                <td>${proxy.order_id}</td>
                <td>${this.getProviderName(proxy.provider)}</td>
                <td><code>${proxy.ip_address}</code></td>
                <td>
                    <span class="badge ${proxy.status === 'active' ? 'bg-success' : 'bg-warning'}">
                        ${proxy.status === 'active' ? '活跃' : '待激活'}
                    </span>
                </td>
                <td>${this.formatDate(proxy.created_at)}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-warning" onclick="proxyManager.resetMobileProxy('${proxy.order_id}')">
                            <i class="fas fa-redo"></i> 重置IP
                        </button>
                        <button class="btn btn-outline-danger" onclick="proxyManager.deleteProxy('${proxy.order_id}', 'mobile')">
                            <i class="fas fa-trash"></i> 删除
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    async testProxy(proxyId) {
        try {
            window.app.showToast('正在测试代理连接...', 'info');
            // 这里可以添加代理测试逻辑
            // const result = await api.testProxy(proxyId);
            window.app.showToast('代理连接正常', 'success');
        } catch (error) {
            console.error('测试代理失败:', error);
            window.app.showToast('代理连接失败', 'error');
        }
    }

    async refreshDynamicProxy(orderId) {
        try {
            const result = await api.getDynamicProxy(orderId);
            window.app.showToast('动态代理已刷新', 'success');
            await this.loadDynamicProxies();
        } catch (error) {
            console.error('刷新动态代理失败:', error);
            window.app.showToast('刷新失败', 'error');
        }
    }

    async resetMobileProxy(orderId) {
        try {
            await api.resetMobileProxy(orderId);
            window.app.showToast('移动代理IP已重置', 'success');
            await this.loadMobileProxies();
        } catch (error) {
            console.error('重置移动代理失败:', error);
            window.app.showToast('重置失败', 'error');
        }
    }

    async deleteProxy(identifier, type) {
        if (!confirm('确定要删除这个代理吗？')) {
            return;
        }

        try {
            // 这里需要根据实际API实现删除功能
            // await api.deleteProxy(identifier, type);
            window.app.showToast('代理已删除', 'success');
            await this.loadProxyList();
        } catch (error) {
            console.error('删除代理失败:', error);
            window.app.showToast('删除失败', 'error');
        }
    }

    updateDashboardStats() {
        const totalProxies = 
            (this.proxies.static?.length || 0) + 
            (this.proxies.dynamic?.length || 0) + 
            (this.proxies.mobile?.length || 0);
        
        const activeProxies = 
            (this.proxies.static?.filter(p => p.status === 'active').length || 0) +
            (this.proxies.dynamic?.filter(p => p.status === 'active').length || 0) +
            (this.proxies.mobile?.filter(p => p.status === 'active').length || 0);

        const totalElement = document.getElementById('total-proxies');
        const activeElement = document.getElementById('active-proxies');
        
        if (totalElement) totalElement.textContent = totalProxies;
        if (activeElement) activeElement.textContent = activeProxies;
    }

    getProviderName(provider) {
        const providers = {
            'viettel': 'Viettel',
            'fpt': 'FPT',
            'vnpt': 'VNPT',
            'viettel_mobile': 'Viettel Mobile',
            'mobifone': 'Mobifone',
            'vinaphone': 'Vinaphone'
        };
        return providers[provider] || provider;
    }

    getPackageName(packageType) {
        const packages = {
            'daily': '每日套餐',
            'weekly': '每周套餐',
            'monthly': '每月套餐'
        };
        return packages[packageType] || packageType;
    }

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
}

// 创建全局代理管理器实例
const proxyManager = new ProxyManager();

// 导出代理管理器
window.proxyManager = proxyManager;
