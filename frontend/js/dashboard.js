// Dashboard module with localization support
class DashboardManager {
    constructor() {
        this.chart = null;
        this.apiKeyWarningShown = false;
        this.initChart();
    }

    initChart() {
        const ctx = document.getElementById('proxyChart');
        if (!ctx) return;

        this.chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: this.getProxyLabels(),
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ['#0f766e', '#0ea5e9', '#f59e0b'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            font: { size: 12 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0) || 1;
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    async loadDashboardData() {
        try {
            await this.loadProxyStats();
            await this.loadApiKeyStats();
            await this.loadRecentActivities();
        } catch (error) {
            console.error('加载仪表板数据失败:', error);
        }
    }

    async loadProxyStats() {
        try {
            if (!api.hasApiKey()) {
                this.setProxyStatsUnavailable();
                this.showApiKeyWarning();
                return;
            }
            const stats = await api.getProxyStats();
            document.getElementById('total-proxies').textContent = stats.total_proxies || 0;
            document.getElementById('active-proxies').textContent = stats.active_proxies || 0;

            if (this.chart) {
                this.chart.data.labels = this.getProxyLabels();
                // 使用后端返回的by_category字段，或者兼容旧的字段名
                const categoryData = stats.by_category || {};
                this.chart.data.datasets[0].data = [
                    categoryData.static || stats.static_proxies || 0,
                    categoryData.dynamic || stats.dynamic_proxies || 0,
                    categoryData.mobile || stats.mobile_proxies || 0
                ];
                this.chart.update();
            }
        } catch (error) {
            console.error('加载代理统计失败:', error);
            if (error?.code === 'API_KEY_REQUIRED') {
                this.setProxyStatsUnavailable();
                this.showApiKeyWarning();
                return;
            }
            document.getElementById('total-proxies').textContent = '0';
            document.getElementById('active-proxies').textContent = '0';
        }
    }

    setProxyStatsUnavailable() {
        document.getElementById('total-proxies').textContent = '--';
        document.getElementById('active-proxies').textContent = '--';
    }

    showApiKeyWarning() {
        if (this.apiKeyWarningShown) return;
        this.apiKeyWarningShown = true;
        const message = i18n?.t('common.apiKeyRequired') || 'Please create an API key before using proxy APIs.';
        if (window.app?.showToast) {
            window.app.showToast(message, 'warning');
        } else {
            alert(message);
        }
    }

    async loadApiKeyStats() {
        try {
            const apiKeys = await api.getApiKeys();
            const activeKeys = apiKeys.filter(key => key.is_active).length;
            document.getElementById('api-keys-count').textContent = activeKeys;
        } catch (error) {
            console.error('加载 API 密钥统计失败:', error);
            document.getElementById('api-keys-count').textContent = '0';
        }
    }

    async loadRecentActivities() {
        try {
            const activities = this.buildSampleActivities();
            this.renderRecentActivities(activities);
        } catch (error) {
            console.error('加载最近活动失败:', error);
            document.getElementById('recent-activities').innerHTML =
                `<p class="text-muted">${i18n?.t('dashboard.activitiesFailed') || '加载活动记录失败'}</p>`;
        }
    }

    renderRecentActivities(activities) {
        const container = document.getElementById('recent-activities');
        if (!activities || activities.length === 0) {
            container.innerHTML =
                `<p class="text-muted">${i18n?.t('dashboard.noActivities') || '暂无活动记录'}</p>`;
            return;
        }

        container.innerHTML = activities.map(activity => `
            <div class="d-flex align-items-center mb-3">
                <div class="me-3">
                    <i class="${activity.icon} ${activity.color}"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="small">${activity.message}</div>
                    <div class="text-muted small">${this.formatDateTime(activity.time)}</div>
                </div>
            </div>
        `).join('');
    }

    formatDateTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) {
            return i18n?.t('common.time.justNow') || '刚刚';
        }
        if (diffMins < 60) {
            return i18n?.t('common.time.minutesAgo', { count: diffMins }) || `${diffMins}分钟前`;
        }
        if (diffHours < 24) {
            return i18n?.t('common.time.hoursAgo', { count: diffHours }) || `${diffHours}小时前`;
        }
        if (diffDays < 7) {
            return i18n?.t('common.time.daysAgo', { count: diffDays }) || `${diffDays}天前`;
        }
        return date.toLocaleDateString(i18n?.currentLang === 'en' ? 'en-US' : 'zh-CN');
    }

    updateApiCallStats() {
        const apiCalls = parseInt(localStorage.getItem('api_calls') || '0', 10);
        document.getElementById('api-calls').textContent = apiCalls;
    }

    incrementApiCallCount() {
        const currentCount = parseInt(localStorage.getItem('api_calls') || '0', 10);
        const newCount = currentCount + 1;
        localStorage.setItem('api_calls', newCount.toString());
        document.getElementById('api-calls').textContent = newCount;
    }

    async refresh() {
        try {
            window.app.showToast(i18n?.t('dashboard.toast.refreshing') || '正在刷新数据...', 'info');
            await this.loadDashboardData();
            window.app.showToast(i18n?.t('dashboard.toast.success') || '数据已更新', 'success');
        } catch (error) {
            console.error('刷新仪表板失败:', error);
            window.app.showToast(i18n?.t('dashboard.toast.failed') || '刷新失败', 'error');
        }
    }

    getProxyLabels() {
        if (window.i18n) {
            return [
                i18n.t('proxy.labels.static'),
                i18n.t('proxy.labels.dynamic'),
                i18n.t('proxy.labels.mobile')
            ];
        }
        return ['Static', 'Dynamic', 'Mobile'];
    }

    buildSampleActivities() {
        return [
            {
                type: 'proxy_purchase',
                message: i18n?.t('dashboard.samples.staticPurchase') || '购买了一条静态代理',
                time: '2024-01-15T10:30:00',
                icon: 'fas fa-shopping-cart',
                color: 'text-primary'
            },
            {
                type: 'api_key_created',
                message: i18n?.t('dashboard.samples.apiCreated') || '创建了新的 API 密钥',
                time: '2024-01-15T09:15:00',
                icon: 'fas fa-key',
                color: 'text-success'
            },
            {
                type: 'proxy_test',
                message: i18n?.t('dashboard.samples.proxyTest') || '测试了代理连接',
                time: '2024-01-15T08:45:00',
                icon: 'fas fa-plug',
                color: 'text-info'
            }
        ];
    }

    getDashboardSummary() {
        return {
            totalProxies: parseInt(document.getElementById('total-proxies').textContent) || 0,
            activeProxies: parseInt(document.getElementById('active-proxies').textContent) || 0,
            apiKeys: parseInt(document.getElementById('api-keys-count').textContent) || 0,
            apiCalls: parseInt(document.getElementById('api-calls').textContent) || 0
        };
    }
}

const dashboardManager = new DashboardManager();
window.dashboardManager = dashboardManager;
