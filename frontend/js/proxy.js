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
        try {
            const response = await api.get('/proxy/list');
            this.groupProxies(response.proxies || []);
            this.renderStaticProxies();
            this.renderDynamicProxies();
            this.renderMobileProxies();
        } catch (error) {
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
                <td colspan="4" class="text-center text-muted">
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
