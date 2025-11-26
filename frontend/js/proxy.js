class ProxyManager {
    constructor() {
        this.proxies = { static: [], dynamic: [], mobile: [] };
        this.handleCopyClick = this.handleCopyClick.bind(this);
        document.addEventListener('click', this.handleCopyClick);
        this.init();
    }

    async init() {
        try {
            await sessionController.initialized;
            await this.loadProxyList();
        } catch (error) {
            console.error('初始化代理页面失败:', error);
            this.showToast(error.message || '加载代理失败', 'error');
        }
    }

    async loadProxyList() {
        if (!api.hasApiKey()) {
            this.renderApiKeyWarning();
            this.showToast(i18n?.t('common.apiKeyRequired') || '请先创建 API Key 再查看代理。', 'warning');
            return;
        }
        try {
            const response = await api.get('/proxy/list');
            this.groupProxies(response.proxies || []);
            this.renderStaticProxies();
            this.renderDynamicProxies();
            this.renderMobileProxies();
        } catch (error) {
            if (error?.code === 'API_KEY_REQUIRED') {
                this.renderApiKeyWarning();
                this.showToast(i18n?.t('common.apiKeyRequired') || '请先创建 API Key 再查看代理。', 'warning');
                return;
            }
            console.error('加载代理列表失败:', error);
            this.showToast(error.message || '加载代理失败', 'error');
            this.renderEmptyState('static-proxies', i18n?.t('proxy.empty.static'));
            this.renderEmptyState('dynamic-proxies', i18n?.t('proxy.empty.dynamic'));
            this.renderEmptyState('mobile-proxies', i18n?.t('proxy.empty.mobile'));
        }
    }

    groupProxies(orders) {
        this.proxies = { static: [], dynamic: [], mobile: [] };
        orders.forEach((order) => {
            if (order.order_id?.startsWith('STATIC_')) {
                this.proxies.static.push(order);
            } else if (order.order_id?.startsWith('DYNAMIC_')) {
                this.proxies.dynamic.push(order);
            } else if (order.order_id?.startsWith('MOBILE_')) {
                this.proxies.mobile.push(order);
            }
        });
    }

    renderApiKeyWarning() {
        const message = i18n?.t('common.apiKeyRequired') || '请先创建 API Key 再查看代理。';
        ['static-proxies', 'dynamic-proxies', 'mobile-proxies'].forEach((id) => {
            const container = document.getElementById(id);
            if (container) {
                container.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center text-muted">
                            <i class="fas fa-key fa-2x mb-2"></i>
                            <div>${message}</div>
                        </td>
                    </tr>
                `;
            }
        });
    }


    renderStaticProxies() {
        const container = document.getElementById('static-proxies');
        if (!container) return;

        if (!this.proxies.static.length) {
            this.renderEmptyState('static-proxies', i18n?.t('proxy.empty.static'));
            return;
        }

        container.innerHTML = this.proxies.static.map((order) => {
            const infoHtml = this.renderStaticInfo(order);
            return `
                <tr>
                    <td>
                        <div class="fw-semibold">${order.order_id}</div>
                        <div class="text-muted small">#${order.id}</div>
                    </td>
                    <td>${infoHtml}</td>
                    <td>${this.formatDate(order.created_at)}</td>
                    <td>${this.formatDate(order.expires_at)}</td>
                    <td>
                        <div class="btn-group" role="group">
                            <button class="btn btn-outline-primary btn-sm" 
                                    onclick="proxyManager.renewStaticProxy('${order.order_id}')"
                                    title="续费">
                                <i class="fas fa-redo"></i>
                            </button>
                            <button class="btn btn-outline-success btn-sm" 
                                    onclick="proxyManager.exportStaticProxies()"
                                    title="导出全部">
                                <i class="fas fa-download"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    renderDynamicProxies() {
        const container = document.getElementById('dynamic-proxies');
        if (!container) return;

        if (!this.proxies.dynamic.length) {
            this.renderEmptyState('dynamic-proxies', i18n?.t('proxy.empty.dynamic'));
            return;
        }

        container.innerHTML = this.proxies.dynamic.map((order) => `
            <tr>
                <td>
                    <div class="fw-semibold">${order.order_id}</div>
                    <div class="text-muted small">${this.formatDate(order.created_at)}</div>
                </td>
                <td>${this.renderTokenCell(order.upstream_id)}</td>
                <td>${this.renderStatusBadge(order.status)}</td>
                <td>${this.formatDate(order.expires_at)}</td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-outline-success btn-sm" 
                                onclick="proxyManager.exportDynamicProxies()"
                                title="导出全部">
                            <i class="fas fa-download"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    renderMobileProxies() {
        const container = document.getElementById('mobile-proxies');
        if (!container) return;

        if (!this.proxies.mobile.length) {
            this.renderEmptyState('mobile-proxies', i18n?.t('proxy.empty.mobile'));
            return;
        }

        container.innerHTML = this.proxies.mobile.map((order) => {
            const info = order.proxy_info || {};
            return `
                <tr>
                    <td>
                        <div class="fw-semibold">${order.order_id}</div>
                        <div class="text-muted small">${this.formatDate(order.created_at)}</div>
                    </td>
                    <td>${this.renderTokenCell(order.upstream_id || info.key_code)}</td>
                    <td>
                        <div class="small text-muted">${info.server || '-'}</div>
                        <div class="small">Port: <code>${info.server_port || '--'}</code></div>
                    </td>
                    <td>${this.formatDate(order.expires_at || info.expired_time)}</td>
                </tr>
            `;
        }).join('');
    }

    renderStaticInfo(order) {
        const info = order.proxy_info || {};
        const authInfo = info.auth || {};
        const provider = info.loaiproxy || info.provider || '-';
        const protocol = (info.type || 'HTTP').toUpperCase();
        const ip = info.ip || info.proxy || info.proxyhttp || info.proxy_http || '-';
        const port = info.port || info.port_proxy || info.porthttp || info.port_http || '-';
        const username = info.user || info.username || authInfo.user || '-';
        const password = info.password || info.pass || authInfo.pass || '-';

        return `
            <div class="mb-1"><span class="badge bg-light text-dark">${provider}</span></div>
            <div class="small text-muted">${protocol}</div>
            <div class="small text-break"><code>${ip}:${port}</code></div>
            <div class="small text-break">
                <span>${i18n?.t('proxy.labels.username') || '用户名'}:</span> <code>${username}</code>
            </div>
            <div class="small text-break">
                <span>${i18n?.t('proxy.labels.password') || '密码'}:</span> <code>${password}</code>
            </div>
        `;
    }

    renderTokenCell(token) {
        if (!token) {
            return `<span class="text-muted">-</span>`;
        }
        return `
            <div class="d-flex align-items-center gap-2">
                <code class="text-break">${token}</code>
                <button class="btn btn-outline-secondary btn-sm" data-copy-token="${token}">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        `;
    }

    renderStatusBadge(status) {
        const active = status === 'active';
        const label = active
            ? (i18n?.t('common.status.active') || '活跃')
            : (i18n?.t('common.status.pending') || '待处理');
        const cls = active ? 'badge bg-success' : 'badge bg-secondary';
        return `<span class="${cls}">${label}</span>`;
    }

    renderEmptyState(containerId, message = '') {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <div>${message || i18n?.t('common.noData') || '暂无数据'}</div>
                </td>
            </tr>
        `;
    }

    handleCopyClick(event) {
        const btn = event.target.closest('[data-copy-token]');
        if (!btn) return;
        const token = btn.getAttribute('data-copy-token');
        if (!token) return;
        navigator.clipboard.writeText(token).then(() => {
            this.showToast(i18n?.t('proxy.toast.tokenCopied') || 'Token 已复制', 'success');
        }).catch(() => {
            this.showToast(i18n?.t('profile.toast.copyFailed') || '复制失败，请稍后再试', 'error');
        });
    }

    formatDate(value) {
        if (!value) return '-';
        try {
            const date = new Date(value);
            return date.toLocaleString(i18n?.currentLang === 'en' ? 'en-US' : 'zh-CN', { hour12: false });
        } catch {
            return value;
        }
    }

    async renewStaticProxy(orderId) {
        try {
            this.showToast('正在续费代理...', 'info');
            
            const response = await api.post(`/proxy/static/${orderId}/renew`);
            
            if (response.renewal_info) {
                const info = response.renewal_info;
                this.showToast(
                    `续费成功！续费${info.duration_days}天，费用：¥${info.amount}，余额：¥${info.new_balance}`,
                    'success'
                );
            } else {
                this.showToast('续费成功！', 'success');
            }
            
            // 刷新代理列表
            await this.loadProxyList();
            
        } catch (error) {
            console.error('续费失败:', error);
            this.showToast(error.message || '续费失败，请稍后再试', 'error');
        }
    }

    async exportStaticProxies() {
        try {
            this.showToast('正在导出静态代理...', 'info');
            
            const response = await api.get('/proxy/static/export');
            
            if (response.content) {
                // 创建下载链接
                const blob = new Blob([response.content], { type: 'text/plain' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = response.filename || 'static_proxies.txt';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showToast(`成功导出${response.count}个静态代理`, 'success');
            } else {
                this.showToast('导出失败：没有找到代理数据', 'error');
            }
            
        } catch (error) {
            console.error('导出静态代理失败:', error);
            this.showToast(error.message || '导出失败，请稍后再试', 'error');
        }
    }

    async exportDynamicProxies() {
        try {
            this.showToast('正在导出动态代理...', 'info');
            
            const response = await api.get('/proxy/dynamic/export');
            
            if (response.content) {
                // 创建下载链接
                const blob = new Blob([response.content], { type: 'text/plain' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = response.filename || 'dynamic_keys.txt';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showToast(`成功导出${response.count}个动态代理密钥`, 'success');
            } else {
                this.showToast('导出失败：没有找到代理数据', 'error');
            }
            
        } catch (error) {
            console.error('导出动态代理失败:', error);
            this.showToast(error.message || '导出失败，请稍后再试', 'error');
        }
    }

    showToast(message, type = 'info') {
        const toastEl = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');
        if (!toastEl || !toastMessage) return;

        toastEl.className = 'toast';
        toastEl.classList.add(
            type === 'success' ? 'bg-success text-white' :
            type === 'error' ? 'bg-danger text-white' :
            type === 'warning' ? 'bg-warning text-dark' :
            'bg-info text-white'
        );
        toastMessage.textContent = message;
        const bsToast = new bootstrap.Toast(toastEl);
        bsToast.show();
    }
}

const proxyManager = new ProxyManager();
window.proxyManager = proxyManager;
