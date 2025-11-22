// 仪表板模块
class DashboardManager {
    constructor() {
        this.chart = null;
        this.initChart();
    }

    initChart() {
        const ctx = document.getElementById('proxyChart');
        if (ctx) {
            this.chart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['静态代理', '动态代理', '移动代理'],
                    datasets: [{
                        data: [0, 0, 0],
                        backgroundColor: [
                            '#0d6efd',
                            '#198754',
                            '#ffc107'
                        ],
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
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    async loadDashboardData() {
        try {
            // 加载代理统计
            await this.loadProxyStats();
            
            // 加载API密钥统计
            await this.loadApiKeyStats();
            
            // 加载最近活动
            await this.loadRecentActivities();
            
        } catch (error) {
            console.error('加载仪表板数据失败:', error);
        }
    }

    async loadProxyStats() {
        try {
            const stats = await api.getProxyStats();
            
            // 更新统计卡片
            document.getElementById('total-proxies').textContent = stats.total_proxies || 0;
            document.getElementById('active-proxies').textContent = stats.active_proxies || 0;
            
            // 更新图表
            if (this.chart) {
                this.chart.data.datasets[0].data = [
                    stats.static_proxies || 0,
                    stats.dynamic_proxies || 0,
                    stats.mobile_proxies || 0
                ];
                this.chart.update();
            }
            
        } catch (error) {
            console.error('加载代理统计失败:', error);
            // 设置默认值
            document.getElementById('total-proxies').textContent = '0';
            document.getElementById('active-proxies').textContent = '0';
        }
    }

    async loadApiKeyStats() {
        try {
            const apiKeys = await api.getApiKeys();
            const activeKeys = apiKeys.filter(key => key.is_active).length;
            
            document.getElementById('api-keys-count').textContent = activeKeys;
            
        } catch (error) {
            console.error('加载API密钥统计失败:', error);
            document.getElementById('api-keys-count').textContent = '0';
        }
    }

    async loadRecentActivities() {
        try {
            // 这里可以添加获取最近活动的API调用
            // const activities = await api.getRecentActivities();
            
            // 模拟最近活动数据
            const activities = [
                {
                    type: 'proxy_purchase',
                    message: '购买了1个Viettel静态代理',
                    time: '2024-01-15 10:30:00',
                    icon: 'fas fa-shopping-cart',
                    color: 'text-primary'
                },
                {
                    type: 'api_key_created',
                    message: '创建了新的API密钥',
                    time: '2024-01-15 09:15:00',
                    icon: 'fas fa-key',
                    color: 'text-success'
                },
                {
                    type: 'proxy_test',
                    message: '测试了代理连接',
                    time: '2024-01-15 08:45:00',
                    icon: 'fas fa-plug',
                    color: 'text-info'
                }
            ];
            
            this.renderRecentActivities(activities);
            
        } catch (error) {
            console.error('加载最近活动失败:', error);
            document.getElementById('recent-activities').innerHTML = 
                '<p class="text-muted">加载活动记录失败</p>';
        }
    }

    renderRecentActivities(activities) {
        const container = document.getElementById('recent-activities');
        
        if (!activities || activities.length === 0) {
            container.innerHTML = '<p class="text-muted">暂无活动记录</p>';
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
            return '刚刚';
        } else if (diffMins < 60) {
            return `${diffMins}分钟前`;
        } else if (diffHours < 24) {
            return `${diffHours}小时前`;
        } else if (diffDays < 7) {
            return `${diffDays}天前`;
        } else {
            return date.toLocaleDateString('zh-CN');
        }
    }

    // 更新API调用统计
    updateApiCallStats() {
        // 这里可以从localStorage或API获取API调用统计
        const apiCalls = parseInt(localStorage.getItem('api_calls') || '0');
        document.getElementById('api-calls').textContent = apiCalls;
    }

    // 增加API调用计数
    incrementApiCallCount() {
        const currentCount = parseInt(localStorage.getItem('api_calls') || '0');
        const newCount = currentCount + 1;
        localStorage.setItem('api_calls', newCount.toString());
        document.getElementById('api-calls').textContent = newCount;
    }

    // 刷新仪表板
    async refresh() {
        try {
            window.app.showToast('正在刷新数据...', 'info');
            await this.loadDashboardData();
            window.app.showToast('数据已更新', 'success');
        } catch (error) {
            console.error('刷新仪表板失败:', error);
            window.app.showToast('刷新失败', 'error');
        }
    }

    // 获取仪表板摘要
    getDashboardSummary() {
        return {
            totalProxies: parseInt(document.getElementById('total-proxies').textContent) || 0,
            activeProxies: parseInt(document.getElementById('active-proxies').textContent) || 0,
            apiKeys: parseInt(document.getElementById('api-keys-count').textContent) || 0,
            apiCalls: parseInt(document.getElementById('api-calls').textContent) || 0
        };
    }
}

// 创建全局仪表板管理器实例
const dashboardManager = new DashboardManager();

// 导出仪表板管理器
window.dashboardManager = dashboardManager;
