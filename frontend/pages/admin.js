const escapeHTML = (value) => {
    if (value === null || value === undefined) {
        return '';
    }
    return String(value).replace(/[&<>"']/g, (char) => {
        switch (char) {
            case '&':
                return '&amp;';
            case '<':
                return '&lt;';
            case '>':
                return '&gt;';
            case '"':
                return '&quot;';
            case '\'':
                return '&#39;';
            default:
                return char;
        }
    });
};

class AdminPage {
    constructor() {
        this.currentTab = 'dashboard';
        this.currentUser = null;
        this.charts = {};
        
        this.init();
    }

    async init() {
        this.bindEvents();
        const hasAccess = await this.checkAdminAccess();
        if (!hasAccess) {
            return;
        }

        try {
            await this.loadUserInfo();
            await this.loadDashboard();
        } catch (error) {
            console.error('AdminPage初始化失败:', error);
            this.showToast('加载管理员数据失败，请刷新页面', 'error');
        }
    }

    bindEvents() {
        // 标签页切换
        document.querySelectorAll('.nav-link[data-tab]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tab = e.currentTarget?.dataset?.tab || e.target.closest('[data-tab]')?.dataset?.tab;
                if (tab) {
                    this.switchTab(tab);
                }
            });
        });

        // 用户搜索
        document.getElementById('searchUserBtn').addEventListener('click', () => {
            this.searchUsers();
        });

        document.getElementById('userSearch').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchUsers();
            }
        });

        // 订单筛选
        document.getElementById('filterOrdersBtn').addEventListener('click', () => {
            this.filterOrders();
        });

        // 余额调整表单
        document.getElementById('balanceForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.adjustUserBalance();
        });

        // 余额调整金额变化
        document.getElementById('adjustAmount').addEventListener('input', (e) => {
            this.calculateNewBalance(e.target.value);
        });

        // 模态框关闭
        document.querySelectorAll('.close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.modal').style.display = 'none';
            });
        });

        // 点击模态框外部关闭
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.style.display = 'none';
            }
        });

        // 产品管理相关事件
        document.getElementById('addProductBtn').addEventListener('click', () => {
            this.editProduct(null);
        });

        document.getElementById('filterProductsBtn').addEventListener('click', () => {
            this.loadProductsList();
        });

        document.getElementById('productForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveProduct();
        });

        // 产品类别变化时更新子类别
        document.getElementById('productCategory').addEventListener('change', (e) => {
            this.updateSubcategoryOptions(e.target.value);
        });

        // 产品映射表单提交
        document.getElementById('mappingForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveMapping();
        });

        // 提供商表单提交
        document.getElementById('providerForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveProvider();
        });

        // 退出登录
        document.getElementById('logoutBtn').addEventListener('click', () => {
            sessionController.logout({ redirectTo: '../pages/login.html' });
        });

        // 添加映射按钮
        document.getElementById('addMappingBtn').addEventListener('click', () => {
            this.editMapping(null);
        });

        // 添加提供商按钮
        document.getElementById('addProviderBtn').addEventListener('click', () => {
            this.editProvider(null);
        });
    }

    async checkAdminAccess() {
        await sessionController.initialized;
        if (!sessionController.isAuthenticated()) {
            await sessionController.safeRefresh();
        }
        if (!sessionController.isAuthenticated()) {
            alert('登录状态已失效，请重新登录');
            window.location.href = '../pages/login.html';
            return false;
        }

        if (!sessionController.isAdmin()) {
            alert('当前账号没有管理员权限，即将返回仪表板');
            window.location.href = '../pages/dashboard.html';
            return false;
        }

        this.currentUser = sessionController.getUser();
        return true;
    }
    async loadUserInfo() {
        try {
            await sessionController.initialized;
            const cachedUser = sessionController.getUser();
            const userInfo = cachedUser || await api.getUserInfo();
            if (userInfo) {
                const balance = Number(userInfo.balance || 0);
                document.getElementById('userBalance').textContent = `$${balance.toFixed(2)}`;
            }
        } catch (error) {
            console.error('Failed to load user info:', error);
        }
    }

    switchTab(tabName) {
        console.log('切换到标签页:', tabName);
        
        // 更新标签页状态
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // 更新内容显示
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        // 加载对应数据
        switch (tabName) {
            case 'dashboard':
                console.log('加载仪表板数据...');
                this.loadDashboard();
                break;
            case 'users':
                console.log('加载用户数据...');
                this.loadUsers();
                break;
            case 'orders':
                console.log('加载订单数据...');
                this.loadOrders();
                break;
            case 'payments':
                console.log('加载支付数据...');
                this.loadPayments();
                break;
            case 'products':
                console.log('加载产品数据...');
                this.loadProducts();
                break;
            case 'mappings':
                console.log('加载产品映射数据...');
                this.loadProductMappings();
                break;
            case 'providers':
                console.log('加载提供商数据...');
                this.loadProviders();
                break;
            case 'finance':
                console.log('加载财务统计...');
                this.loadFinanceStats();
                break;
        }
    }

    async loadDashboard() {
        try {
            console.log('开始加载仪表板数据...');
            this.showLoading();
            
            const stats = await api.get('/admin/stats/dashboard');
            console.log('仪表板数据响应:', stats);
            
            // 更新统计卡片 - 添加安全检查
            if (stats && stats.finance) {
                const totalUsersEl = document.getElementById('totalUsers');
                const totalRevenueEl = document.getElementById('totalRevenue');
                const totalOrdersEl = document.getElementById('totalOrders');
                const activeUsersEl = document.getElementById('activeUsers');
                
                if (totalUsersEl) totalUsersEl.textContent = stats.finance.total_users || 0;
                if (totalRevenueEl) totalRevenueEl.textContent = `$${stats.finance.total_revenue || 0}`;
                if (totalOrdersEl) totalOrdersEl.textContent = stats.finance.order_stats?.total_orders || 0;
                if (activeUsersEl) activeUsersEl.textContent = stats.finance.active_users || 0;
            }
            
            // 更新最近活动
            if (stats && stats.recent_activities) {
                this.renderRecentActivities(stats.recent_activities);
            }
            
            // 更新收入趋势图表
            if (stats && stats.daily_orders) {
                this.renderRevenueChart(stats.daily_orders);
            }
            
            console.log('仪表板数据加载完成');
            
        } catch (error) {
            console.error('Failed to load dashboard:', error);
            console.error('错误详情:', error.message);
            console.error('错误状态:', error.status);
            this.showToast('加载仪表板失败: ' + (error.message || '未知错误'), 'error');
        } finally {
            this.hideLoading();
        }
    }

    renderRecentActivities(activities) {
        const container = document.getElementById('recentActivities');
        
        if (activities.length === 0) {
            container.innerHTML = '<p class="text-muted">暂无活动记录</p>';
            return;
        }

        container.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="${activity.icon} ${activity.color}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-message">${escapeHTML(activity.message)}</div>
                    <div class="activity-time">${new Date(activity.time).toLocaleString()}</div>
                </div>
            </div>
        `).join('');
    }

    renderRevenueChart(dailyOrders) {
        const ctx = document.getElementById('revenueChart').getContext('2d');
        
        if (this.charts.revenue) {
            this.charts.revenue.destroy();
        }

        this.charts.revenue = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dailyOrders.map(item => item.date),
                datasets: [{
                    label: '收入',
                    data: dailyOrders.map(item => item.revenue),
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }, {
                    label: '订单数',
                    data: dailyOrders.map(item => item.orders),
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
    }

    async loadUsers() {
        try {
            this.showLoading();
            
            const users = await api.get('/admin/users');
            this.renderUsers(users);
        } catch (error) {
            console.error('Failed to load users:', error);
            this.showToast('加载用户列表失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    renderUsers(users) {
        const tbody = document.getElementById('usersTableBody');
        
        if (users.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        <i class="fas fa-users fa-2x mb-2"></i>
                        <p>暂无用户</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = users.map(user => `
            <tr>
                <td>${user.id}</td>
                <td>${escapeHTML(user.username)}</td>
                <td>${escapeHTML(user.email)}</td>
                <td>$${user.balance}</td>
                <td>
                    <span class="status ${user.is_active ? 'active' : 'inactive'}">
                        ${user.is_active ? '活跃' : '禁用'}
                    </span>
                </td>
                <td>${new Date(user.created_at).toLocaleString()}</td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline" onclick="adminPage.viewUser(${user.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="adminPage.toggleUser(${user.id})">
                            <i class="fas fa-${user.is_active ? 'ban' : 'check'}"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="adminPage.adjustBalance(${user.id}, ${user.balance})">
                            <i class="fas fa-wallet"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    async searchUsers() {
        const searchTerm = document.getElementById('userSearch').value.trim();
        
        try {
            this.showLoading();
            
            const params = {};
            if (searchTerm) {
                params.search = searchTerm;
            }
            
            const users = await api.get('/admin/users', { params });
            this.renderUsers(users);
        } catch (error) {
            console.error('Failed to search users:', error);
            this.showToast('搜索用户失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async viewUser(userId) {
        try {
            this.showLoading();
            
            const user = await api.get(`/admin/users/${userId}`);
            this.showUserModal(user);
        } catch (error) {
            console.error('Failed to load user:', error);
            this.showToast('加载用户详情失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async toggleUser(userId) {
        try {
            this.showLoading();
            
            await api.put(`/admin/users/${userId}/toggle`);
            this.showToast('用户状态更新成功', 'success');
            this.loadUsers();
        } catch (error) {
            console.error('Failed to toggle user:', error);
            this.showToast('更新用户状态失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    adjustBalance(userId, currentBalance) {
        this.currentUserId = userId;
        
        document.getElementById('currentBalance').value = `$${currentBalance}`;
        document.getElementById('adjustAmount').value = '';
        document.getElementById('adjustReason').value = '';
        document.getElementById('newBalance').value = `$${currentBalance}`;
        
        document.getElementById('balanceModal').style.display = 'block';
    }

    calculateNewBalance(adjustAmount) {
        const currentBalance = parseFloat(document.getElementById('currentBalance').value.replace('$', ''));
        const newBalance = currentBalance + (parseFloat(adjustAmount) || 0);
        document.getElementById('newBalance').value = `$${newBalance.toFixed(2)}`;
    }

    async adjustUserBalance() {
        const amount = parseFloat(document.getElementById('adjustAmount').value);
        const description = document.getElementById('adjustReason').value;
        
        if (!amount || !description) {
            this.showToast('请填写完整信息', 'error');
            return;
        }

        try {
            this.showLoading();
            
            await api.post(`/admin/users/${this.currentUserId}/adjust-balance`, {
                amount: amount,
                description: description
            });
            
            this.showToast('余额调整成功', 'success');
            this.closeModal('balanceModal');
            this.loadUsers();
        } catch (error) {
            console.error('Failed to adjust balance:', error);
            this.showToast('调整余额失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    showUserModal(user) {
        const modal = document.getElementById('userModal');
        const modalBody = document.getElementById('userModalBody');
        
        modalBody.innerHTML = `
            <div class="user-details">
                <div class="detail-section">
                    <h5>基本信息</h5>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <label>用户ID:</label>
                            <span>${user.id}</span>
                        </div>
                        <div class="detail-item">
                            <label>用户名:</label>
                            <span>${user.username}</span>
                        </div>
                        <div class="detail-item">
                            <label>邮箱:</label>
                            <span>${user.email}</span>
                        </div>
                        <div class="detail-item">
                            <label>余额:</label>
                            <span>$${user.balance}</span>
                        </div>
                        <div class="detail-item">
                            <label>状态:</label>
                            <span class="status ${user.is_active ? 'active' : 'inactive'}">
                                ${user.is_active ? '活跃' : '禁用'}
                            </span>
                        </div>
                        <div class="detail-item">
                            <label>注册时间:</label>
                            <span>${new Date(user.created_at).toLocaleString()}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        modal.style.display = 'block';
    }

    async loadOrders() {
        try {
            this.showLoading();
            
            const orders = await api.get('/admin/orders');
            this.renderOrders(orders.orders);
        } catch (error) {
            console.error('Failed to load orders:', error);
            this.showToast('加载订单列表失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    renderOrders(orders) {
        const tbody = document.getElementById('ordersTableBody');
        
        if (orders.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        <i class="fas fa-shopping-cart fa-2x mb-2"></i>
                        <p>暂无订单</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = orders.map(order => `
            <tr>
                <td>${order.order_number}</td>
                <td>用户${order.user_id}</td>
                <td>
                    <span class="badge badge-${order.type === 'purchase' ? 'primary' : 'success'}">
                        ${order.type === 'purchase' ? '购买' : '充值'}
                    </span>
                </td>
                <td>$${order.amount}</td>
                <td>
                    <span class="status ${order.status}">
                        ${this.getStatusText(order.status)}
                    </span>
                </td>
                <td>${new Date(order.created_at).toLocaleString()}</td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="adminPage.viewOrder(${order.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    async filterOrders() {
        const status = document.getElementById('orderStatusFilter').value;
        
        try {
            this.showLoading();
            
            const params = {};
            if (status) {
                params.status = status;
            }
            
            const orders = await api.get('/admin/orders', { params });
            this.renderOrders(orders.orders);
        } catch (error) {
            console.error('Failed to filter orders:', error);
            this.showToast('筛选订单失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async loadPayments() {
        try {
            this.showLoading();
            
            const payments = await api.get('/admin/payments');
            this.renderPayments(payments);
        } catch (error) {
            console.error('Failed to load payments:', error);
            this.showToast('加载支付列表失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    renderPayments(payments) {
        const tbody = document.getElementById('paymentsTableBody');
        
        if (payments.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted">
                        <i class="fas fa-credit-card fa-2x mb-2"></i>
                        <p>暂无支付记录</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = payments.map(payment => `
            <tr>
                <td>${payment.payment_id}</td>
                <td>订单${payment.order_id}</td>
                <td>用户${payment.user_id}</td>
                <td>$${payment.amount}</td>
                <td>${payment.method}</td>
                <td>
                    <span class="status ${payment.status}">
                        ${payment.status}
                    </span>
                </td>
                <td>${payment.confirmations} / ${payment.required_confirmations}</td>
                <td>${new Date(payment.created_at).toLocaleString()}</td>
            </tr>
        `).join('');
    }

    async loadFinanceStats() {
        try {
            this.showLoading();
            
            const [orderStats, paymentStats] = await Promise.all([
                api.get('/admin/stats/orders'),
                api.get('/admin/stats/payments')
            ]);
            
            this.renderOrderStatsChart(orderStats);
            this.renderPaymentStatsChart(paymentStats);
        } catch (error) {
            console.error('Failed to load finance stats:', error);
            this.showToast('加载财务统计失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    renderOrderStatsChart(stats) {
        const ctx = document.getElementById('orderStatsChart').getContext('2d');
        
        if (this.charts.orderStats) {
            this.charts.orderStats.destroy();
        }

        this.charts.orderStats = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['待支付', '已支付', '已完成', '已取消'],
                datasets: [{
                    data: [
                        stats.pending_orders,
                        stats.paid_orders,
                        stats.completed_orders,
                        stats.cancelled_orders
                    ],
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    renderPaymentStatsChart(stats) {
        const ctx = document.getElementById('paymentStatsChart').getContext('2d');
        
        if (this.charts.paymentStats) {
            this.charts.paymentStats.destroy();
        }

        this.charts.paymentStats = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['总支付', '加密货币支付', '成功率'],
                datasets: [{
                    label: '数量',
                    data: [
                        stats.total_payments,
                        stats.crypto_payments,
                        stats.success_rate
                    ],
                    backgroundColor: [
                        '#36A2EB',
                        '#FF6384',
                        '#4BC0C0'
                    ]
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    getStatusText(status) {
        const statusMap = {
            'pending': '待支付',
            'paid': '已支付',
            'completed': '已完成',
            'cancelled': '已取消',
            'refunded': '已退款'
        };
        return statusMap[status] || status;
    }

    closeModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type}`;
        toast.style.display = 'block';
        
        setTimeout(() => {
            toast.style.display = 'none';
        }, 3000);
    }

    showLoading(message = '加载中...') {
        const loading = document.createElement('div');
        loading.id = 'loadingOverlay';
        loading.className = 'loading-overlay';
        loading.innerHTML = `
            <div class="loading-spinner">
                <i class="fas fa-spinner fa-spin"></i>
                <p>${message}</p>
            </div>
        `;
        document.body.appendChild(loading);
    }

    hideLoading() {
        const loading = document.getElementById('loadingOverlay');
        if (loading) {
            loading.remove();
        }
    }

    // 产品管理相关方法
    async loadProducts() {
        try {
            this.showLoading();
            
            // 加载产品统计
            const stats = await api.get('/admin/proxy-products/stats');
            this.renderProductStats(stats);
            
            // 加载产品列表
            await this.loadProductsList();
            
            // 加载产品类别和提供商
            await this.loadProductFilters();
            
        } catch (error) {
            console.error('Failed to load products:', error);
            this.showToast('加载产品数据失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async loadProductsList() {
        try {
            const params = {
                page: 1,
                size: 50
            };
            
            // 添加筛选参数
            const category = document.getElementById('productCategoryFilter').value;
            const provider = document.getElementById('productProviderFilter').value;
            const is_active = document.getElementById('productStatusFilter').value;
            
            if (category) params.category = category;
            if (provider) params.provider = provider;
            if (is_active) params.is_active = is_active === 'true';
            
            const products = await api.get('/admin/proxy-products', { params });
            this.renderProducts(products);
        } catch (error) {
            console.error('Failed to load products list:', error);
            this.showToast('加载产品列表失败', 'error');
        }
    }

    async loadProductFilters() {
        try {
            const categories = await api.get('/admin/proxy-products/categories');
            
            // 更新提供商筛选器
            const providerFilter = document.getElementById('productProviderFilter');
            providerFilter.innerHTML = '<option value="">全部提供商</option>';
            
            if (categories.categories && categories.categories.length > 0) {
                const allProviders = new Set();
                categories.categories.forEach(cat => {
                    if (cat.providers) {
                        cat.providers.forEach(provider => allProviders.add(provider));
                    }
                });
                
                Array.from(allProviders).sort().forEach(provider => {
                    const option = document.createElement('option');
                    option.value = provider;
                    option.textContent = provider;
                    providerFilter.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load product filters:', error);
        }
    }

    renderProductStats(stats) {
        document.getElementById('totalProducts').textContent = stats.total_products;
        document.getElementById('activeProducts').textContent = stats.active_products;
        document.getElementById('inactiveProducts').textContent = stats.inactive_products;
        
        // 计算平均价格
        let avgPrice = 0;
        if (stats.category_stats && stats.category_stats.length > 0) {
            const totalPrice = stats.category_stats.reduce((sum, cat) => sum + cat.avg_price, 0);
            avgPrice = totalPrice / stats.category_stats.length;
        }
        document.getElementById('avgPrice').textContent = `$${avgPrice.toFixed(2)}`;
    }

    renderProducts(products) {
        const tbody = document.getElementById('productsTableBody');
        
        if (products.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="11" class="text-center text-muted">
                        <i class="fas fa-box fa-2x mb-2"></i>
                        <p>暂无产品</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = products.map(product => `
            <tr>
                <td>${product.id}</td>
                <td>
                    <span class="badge badge-${this.getCategoryBadgeClass(product.category)}">
                        ${this.getCategoryText(product.category)}
                    </span>
                </td>
                <td>${escapeHTML(product.subcategory || '-')}</td>
                <td>${escapeHTML(product.provider)}</td>
                <td>${escapeHTML(product.product_name)}</td>
                <td>$${product.price}</td>
                <td>${product.duration_days}</td>
                <td>${product.stock}</td>
                <td>
                    <span class="status ${product.is_active ? 'active' : 'inactive'}">
                        ${product.is_active ? '启用' : '停用'}
                    </span>
                </td>
                <td>${new Date(product.created_at).toLocaleString()}</td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline" onclick="window.adminPage.viewProduct(${product.id})" title="查看详情">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="window.adminPage.editProduct(${product.id})" title="编辑">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="window.adminPage.toggleProduct(${product.id})" title="切换状态">
                            <i class="fas fa-${product.is_active ? 'ban' : 'check'}"></i>
                        </button>
                        <button class="btn btn-sm btn-outline text-danger" onclick="window.adminPage.deleteProduct(${product.id})" title="删除">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    getCategoryBadgeClass(category) {
        const classMap = {
            'static': 'primary',
            'dynamic': 'success',
            'mobile': 'warning'
        };
        return classMap[category] || 'secondary';
    }

    getCategoryText(category) {
        const textMap = {
            'static': '静态代理',
            'dynamic': '动态代理',
            'mobile': '移动代理'
        };
        return textMap[category] || category;
    }

    async viewProduct(productId) {
        try {
            this.showLoading();
            
            const product = await api.get(`/admin/proxy-products/${productId}`);
            this.showProductDetailModal(product);
        } catch (error) {
            console.error('Failed to load product:', error);
            this.showToast('加载产品详情失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    showProductDetailModal(product) {
        const modal = document.getElementById('productDetailModal');
        const modalBody = document.getElementById('productDetailBody');
        
        modalBody.innerHTML = `
            <div class="product-details">
                <div class="detail-section">
                    <h5>基本信息</h5>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <label>产品ID:</label>
                            <span>${product.id}</span>
                        </div>
                        <div class="detail-item">
                            <label>产品类别:</label>
                            <span class="badge badge-${this.getCategoryBadgeClass(product.category)}">
                                ${this.getCategoryText(product.category)}
                            </span>
                        </div>
                        <div class="detail-item">
                            <label>子类别:</label>
                            <span>${escapeHTML(product.subcategory || '-')}</span>
                        </div>
                        <div class="detail-item">
                            <label>提供商:</label>
                            <span>${escapeHTML(product.provider)}</span>
                        </div>
                        <div class="detail-item">
                            <label>产品名称:</label>
                            <span>${escapeHTML(product.product_name)}</span>
                        </div>
                        <div class="detail-item">
                            <label>价格:</label>
                            <span class="text-success fw-bold">$${product.price}</span>
                        </div>
                        <div class="detail-item">
                            <label>有效天数:</label>
                            <span>${product.duration_days} 天</span>
                        </div>
                        <div class="detail-item">
                            <label>库存数量:</label>
                            <span>${product.stock}</span>
                        </div>
                        <div class="detail-item">
                            <label>状态:</label>
                            <span class="status ${product.is_active ? 'active' : 'inactive'}">
                                ${product.is_active ? '启用' : '停用'}
                            </span>
                        </div>
                        <div class="detail-item">
                            <label>创建时间:</label>
                            <span>${new Date(product.created_at).toLocaleString()}</span>
                        </div>
                        <div class="detail-item">
                            <label>更新时间:</label>
                            <span>${product.updated_at ? new Date(product.updated_at).toLocaleString() : '-'}</span>
                        </div>
                    </div>
                </div>
                ${product.description ? `
                <div class="detail-section">
                    <h5>产品描述</h5>
                    <p>${escapeHTML(product.description)}</p>
                </div>
                ` : ''}
            </div>
        `;
        
        modal.style.display = 'block';
    }

    editProduct(productId) {
        this.currentProductId = productId;
        
        if (productId) {
            // 编辑模式 - 加载产品数据
            this.loadProductForEdit(productId);
        } else {
            // 添加模式 - 清空表单
            this.clearProductForm();
            document.getElementById('productModalTitle').innerHTML = '<i class="fas fa-box"></i> 添加代理产品';
            document.getElementById('productModal').style.display = 'block';
        }
    }

    async loadProductForEdit(productId) {
        try {
            this.showLoading();
            
            const product = await api.get(`/admin/proxy-products/${productId}`);
            
            // 填充表单
            document.getElementById('productId').value = product.id;
            document.getElementById('productCategory').value = product.category;
            document.getElementById('productProvider').value = product.provider;
            
            // 先更新子类别选项，再设置值
            this.updateSubcategoryOptions(product.category);
            this.updateProviderFieldState(product.category, product.provider);
            document.getElementById('productSubcategory').value = product.subcategory || '';
            
            document.getElementById('productName').value = product.product_name;
            document.getElementById('productPrice').value = product.price;
            document.getElementById('productDuration').value = product.duration_days;
            document.getElementById('productStock').value = product.stock;
            document.getElementById('productDescription').value = product.description || '';
            const price30Input = document.getElementById('productPrice30');
            const price60Input = document.getElementById('productPrice60');
            const price90Input = document.getElementById('productPrice90');
            if (price30Input) price30Input.value = product.price_30 ?? '';
            if (price60Input) price60Input.value = product.price_60 ?? '';
            if (price90Input) price90Input.value = product.price_90 ?? '';
            document.getElementById('productIsActive').checked = product.is_active;
            
            document.getElementById('productModalTitle').innerHTML = '<i class="fas fa-edit"></i> 编辑代理产品';
            document.getElementById('productModal').style.display = 'block';
            
        } catch (error) {
            console.error('Failed to load product for edit:', error);
            this.showToast('加载产品信息失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    clearProductForm() {
        document.getElementById('productForm').reset();
        document.getElementById('productId').value = '';
        document.getElementById('productIsActive').checked = true;
        const price30 = document.getElementById('productPrice30');
        const price60 = document.getElementById('productPrice60');
        const price90 = document.getElementById('productPrice90');
        if (price30) price30.value = '';
        if (price60) price60.value = '';
        if (price90) price90.value = '';
        this.updateSubcategoryOptions('');
        this.updateProviderFieldState('', '');
    }


    async saveProduct() {
        const productId = document.getElementById('productId').value;
        const isEdit = !!productId;
        
        const category = document.getElementById('productCategory').value;
        const providerInput = document.getElementById('productProvider');
        const rawProvider = providerInput?.value?.trim() || '';
        const normalizedProvider = category === 'static'
            ? ((providerInput?.disabled || !rawProvider) ? 'generic' : rawProvider)
            : rawProvider;

        const productData = {
            category,
            provider: normalizedProvider,
            subcategory: document.getElementById('productSubcategory').value || null,
            product_name: document.getElementById('productName').value,
            price: this.parseNumericInput('productPrice'),
            duration_days: this.parseIntegerInput('productDuration'),
            stock: this.parseIntegerInput('productStock', 0),
            description: document.getElementById('productDescription').value || null,
            is_active: document.getElementById('productIsActive').checked
        };

        // 静态代理也使用简单的单价格模式
        if (category === 'static') {
            if (productData.price === null) {
                this.showToast('请提供有效的价格', 'error');
                return;
            }
            if (productData.duration_days === null) {
                productData.duration_days = 30; // 默认30天
            }
        }

        if (!productData.category || !productData.product_name) {
            this.showToast('请填写必填字段', 'error');
            return;
        }

        if (category !== 'static' && !productData.provider) {
            this.showToast('请指定提供商', 'error');
            return;
        }

        if (productData.price === null || productData.duration_days === null) {
            this.showToast('请提供有效的价格和时长', 'error');
            return;
        }

        try {
            this.showLoading();
            
            if (isEdit) {
                await api.put(`/admin/proxy-products/${productId}`, productData);
                this.showToast('产品更新成功', 'success');
            } else {
                await api.post('/admin/proxy-products', productData);
                this.showToast('产品创建成功', 'success');
            }
            
            this.closeModal('productModal');
            this.loadProducts();
            
        } catch (error) {
            console.error('Failed to save product:', error);
            this.showToast(isEdit ? '更新产品失败' : '创建产品失败', 'error');
        } finally {
            this.hideLoading();
        }
    }
    async toggleProduct(productId) {
        try {
            this.showLoading();
            
            await api.put(`/admin/proxy-products/${productId}/toggle`);
            this.showToast('产品状态更新成功', 'success');
            this.loadProducts();
            
        } catch (error) {
            console.error('Failed to toggle product:', error);
            this.showToast('更新产品状态失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async deleteProduct(productId) {
        if (!confirm('确定要删除这个产品吗？此操作不可恢复。')) {
            return;
        }
        
        try {
            this.showLoading();
            
            await api.delete(`/admin/proxy-products/${productId}`);
            this.showToast('产品删除成功', 'success');
            this.loadProducts();
            
        } catch (error) {
            console.error('Failed to delete product:', error);
            this.showToast('删除产品失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // 根据产品类别更新子类别选项
    updateSubcategoryOptions(category) {
        const subcategorySelect = document.getElementById('productSubcategory');
        subcategorySelect.innerHTML = '<option value="">Select subcategory</option>';

        const subcategoryOptions = {
            'static': [
                { value: 'home', text: 'Residential (home)' },
                { value: 'vn_datacenter', text: 'Vietnam datacenter' },
                { value: 'us_datacenter', text: 'US datacenter' }
            ],
            'dynamic': [
                { value: 'home', text: 'Residential (home)' }
            ],
            'mobile': [
                { value: 'mobile', text: 'Mobile proxy' }
            ]
        };

        if (subcategoryOptions[category]) {
            subcategoryOptions[category].forEach(option => {
                const optionElement = document.createElement('option');
                optionElement.value = option.value;
                optionElement.textContent = option.text;
                subcategorySelect.appendChild(optionElement);
            });
        }

        this.toggleStaticPricingFields(category === 'static');
        this.updateProviderFieldState(category, document.getElementById('productProvider').value);
    }

    toggleStaticPricingFields(enable) {
        const staticFields = document.getElementById('staticPricingFields');
        const generalFields = document.getElementById('generalPricingFields');
        const priceInput = document.getElementById('productPrice');
        const durationInput = document.getElementById('productDuration');

        // 静态代理也使用通用定价字段，不再显示多时长设置
        if (staticFields && generalFields) {
            staticFields.classList.add('d-none');
            generalFields.classList.remove('d-none');
            if (priceInput) priceInput.required = true;
            if (durationInput) durationInput.required = true;
        }
    }

    updateProviderFieldState(category, providerValue = '') {
        const providerInput = document.getElementById('productProvider');
        const providerHelp = document.getElementById('providerHelpText');
        if (!providerInput) return;

        // 对于静态代理，也允许编辑提供商字段
        if (category === 'static') {
            providerInput.disabled = false;
            providerInput.placeholder = '如: Viettel, FPT, VNPT, US, DatacenterA, DatacenterB, DatacenterC';
            if (providerHelp) {
                providerHelp.textContent = '静态代理提供商：Viettel, FPT, VNPT, US, DatacenterA, DatacenterB, DatacenterC, GoiViettel, GoiVNPT, GoiDATACENTER';
                providerHelp.classList.remove('d-none');
            }
            // 如果没有提供值，设置为空而不是默认值
            if (!providerValue) {
                providerInput.value = '';
            } else {
                providerInput.value = providerValue;
            }
        } else {
            providerInput.disabled = false;
            providerInput.placeholder = '如: Viettel, FPT, VNPT';
            if (providerHelp) providerHelp.classList.add('d-none');
            providerInput.value = providerValue || '';
        }
    }

    parseNumericInput(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return null;
        const rawValue = (element.value || '').trim();
        if (rawValue === '') return null;
        const parsed = parseFloat(rawValue);
        return Number.isNaN(parsed) ? null : parsed;
    }

    parseIntegerInput(elementId, defaultValue = null) {
        const element = document.getElementById(elementId);
        if (!element) return defaultValue;
        const rawValue = (element.value || '').trim();
        if (rawValue === '') return defaultValue;
        const parsed = parseInt(rawValue, 10);
        return Number.isNaN(parsed) ? defaultValue : parsed;
    }

    parseNumericInput(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return null;
        const rawValue = (element.value || '').trim();
        if (rawValue === '') return null;
        const parsed = parseFloat(rawValue);
        return Number.isNaN(parsed) ? null : parsed;
    }

    parseIntegerInput(elementId, defaultValue = null) {
        const element = document.getElementById(elementId);
        if (!element) return defaultValue;
        const rawValue = (element.value || '').trim();
        if (rawValue === '') return defaultValue;
        const parsed = parseInt(rawValue, 10);
        return Number.isNaN(parsed) ? defaultValue : parsed;
    }

    // 产品映射管理相关方法
    async loadProductMappings() {
        try {
            this.showLoading();
            
            // 并行加载提供商列表和产品选项
            const [providers, products] = await Promise.all([
                api.get('/admin/upstream-providers'),
                api.get('/admin/proxy-products')
            ]);
            
            this.renderProvidersList(providers);
            this.loadProductOptions(products);
            
            // 加载产品映射列表
            await this.loadProductMappingsList();
            
        } catch (error) {
            console.error('Failed to load product mappings:', error);
            this.showToast('加载产品映射失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async loadProductMappingsList() {
        try {
            const params = {
                page: 1,
                size: 50
            };
            
            // 添加筛选参数
            const productId = document.getElementById('mappingProductFilter').value;
            const providerId = document.getElementById('mappingProviderFilter').value;
            const is_active = document.getElementById('mappingStatusFilter').value;
            
            if (productId) params.product_id = productId;
            if (providerId) params.provider_id = providerId;
            if (is_active) params.is_active = is_active === 'true';
            
            const mappings = await api.get('/admin/product-mappings', { params });
            this.renderProductMappings(mappings);
        } catch (error) {
            console.error('Failed to load product mappings list:', error);
            this.showToast('加载产品映射列表失败', 'error');
        }
    }

    renderProvidersList(providers) {
        const providerSelect = document.getElementById('mappingProviderFilter');
        const editProviderSelect = document.getElementById('mappingProvider');
        
        // 清空现有选项
        providerSelect.innerHTML = '<option value="">全部提供商</option>';
        editProviderSelect.innerHTML = '<option value="">选择提供商</option>';
        
        providers.forEach(provider => {
            const option1 = document.createElement('option');
            option1.value = provider.id;
            option1.textContent = provider.display_name;
            providerSelect.appendChild(option1);
            
            const option2 = document.createElement('option');
            option2.value = provider.id;
            option2.textContent = provider.display_name;
            editProviderSelect.appendChild(option2);
        });
    }

    loadProductOptions(products) {
        try {
            const productSelect = document.getElementById('mappingProduct');
            const productFilter = document.getElementById('mappingProductFilter');
            
            // 清空现有选项
            productSelect.innerHTML = '<option value="">选择产品</option>';
            productFilter.innerHTML = '<option value="">全部产品</option>';
            
            products.forEach(product => {
                const option1 = document.createElement('option');
                option1.value = product.id;
                option1.textContent = product.product_name;
                productSelect.appendChild(option1);
                
                const option2 = document.createElement('option');
                option2.value = product.id;
                option2.textContent = product.product_name;
                productFilter.appendChild(option2);
            });
        } catch (error) {
            console.error('Failed to load product options:', error);
        }
    }

    renderProductMappings(mappings) {
        const tbody = document.getElementById('mappingsTableBody');
        
        if (mappings.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted">
                        <i class="fas fa-link fa-2x mb-2"></i>
                        <p>暂无产品映射</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = mappings.map(mapping => `
            <tr>
                <td>${mapping.id}</td>
                <td>${mapping.product ? mapping.product.product_name : '-'}</td>
                <td>${mapping.provider ? mapping.provider.display_name : '-'}</td>
                <td>${mapping.upstream_product_code}</td>
                <td>${mapping.price_multiplier}</td>
                <td>
                    <span class="status ${mapping.is_active ? 'active' : 'inactive'}">
                        ${mapping.is_active ? '启用' : '停用'}
                    </span>
                </td>
                <td>${new Date(mapping.created_at).toLocaleString()}</td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline" onclick="window.adminPage.viewMapping(${mapping.id})" title="查看详情">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="window.adminPage.editMapping(${mapping.id})" title="编辑">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="window.adminPage.toggleMapping(${mapping.id})" title="切换状态">
                            <i class="fas fa-${mapping.is_active ? 'ban' : 'check'}"></i>
                        </button>
                        <button class="btn btn-sm btn-outline text-danger" onclick="window.adminPage.deleteMapping(${mapping.id})" title="删除">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    editMapping(mappingId) {
        this.currentMappingId = mappingId;
        
        if (mappingId) {
            // 编辑模式 - 加载映射数据
            this.loadMappingForEdit(mappingId);
        } else {
            // 添加模式 - 清空表单
            this.clearMappingForm();
            document.getElementById('mappingModalTitle').innerHTML = '<i class="fas fa-link"></i> 添加产品映射';
            document.getElementById('mappingModal').style.display = 'block';
        }
    }

    async loadMappingForEdit(mappingId) {
        try {
            this.showLoading();
            
            const mapping = await api.get(`/admin/product-mappings/${mappingId}`);
            
            // 填充表单
            document.getElementById('mappingId').value = mapping.id;
            document.getElementById('mappingProduct').value = mapping.product_id;
            document.getElementById('mappingProvider').value = mapping.provider_id;
            document.getElementById('mappingUpstreamCode').value = mapping.upstream_product_code;
            document.getElementById('mappingPriceMultiplier').value = mapping.price_multiplier;
            document.getElementById('mappingParams').value = mapping.upstream_params ? JSON.stringify(mapping.upstream_params, null, 2) : '';
            document.getElementById('mappingIsActive').checked = mapping.is_active;
            
            document.getElementById('mappingModalTitle').innerHTML = '<i class="fas fa-edit"></i> 编辑产品映射';
            document.getElementById('mappingModal').style.display = 'block';
            
        } catch (error) {
            console.error('Failed to load mapping for edit:', error);
            this.showToast('加载映射信息失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    clearMappingForm() {
        document.getElementById('mappingForm').reset();
        document.getElementById('mappingId').value = '';
        document.getElementById('mappingIsActive').checked = true;
    }

    async saveMapping() {
        const mappingId = document.getElementById('mappingId').value;
        const isEdit = !!mappingId;
        
        let upstreamParams = null;
        try {
            const paramsText = document.getElementById('mappingParams').value.trim();
            if (paramsText) {
                upstreamParams = JSON.parse(paramsText);
            }
        } catch (error) {
            this.showToast('API参数格式错误，请输入有效的JSON', 'error');
            return;
        }
        
        const mappingData = {
            product_id: parseInt(document.getElementById('mappingProduct').value),
            provider_id: parseInt(document.getElementById('mappingProvider').value),
            upstream_product_code: document.getElementById('mappingUpstreamCode').value,
            upstream_params: upstreamParams,
            price_multiplier: parseFloat(document.getElementById('mappingPriceMultiplier').value) || 1.000,
            is_active: document.getElementById('mappingIsActive').checked
        };
        
        // 验证必填字段
        if (!mappingData.product_id || !mappingData.provider_id || !mappingData.upstream_product_code) {
            this.showToast('请填写必填字段', 'error');
            return;
        }
        
        try {
            this.showLoading();
            
            if (isEdit) {
                await api.put(`/admin/product-mappings/${mappingId}`, mappingData);
                this.showToast('产品映射更新成功', 'success');
            } else {
                await api.post('/admin/product-mappings', mappingData);
                this.showToast('产品映射添加成功', 'success');
            }
            
            this.closeModal('mappingModal');
            this.loadProductMappings();
            
        } catch (error) {
            console.error('Failed to save mapping:', error);
            this.showToast(isEdit ? '更新产品映射失败' : '添加产品映射失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async viewMapping(mappingId) {
        try {
            this.showLoading();
            
            const mapping = await api.get(`/admin/product-mappings/${mappingId}`);
            this.showMappingDetailModal(mapping);
        } catch (error) {
            console.error('Failed to load mapping:', error);
            this.showToast('加载映射详情失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    showMappingDetailModal(mapping) {
        const modal = document.getElementById('mappingDetailModal');
        const modalBody = document.getElementById('mappingDetailBody');
        
        modalBody.innerHTML = `
            <div class="mapping-details">
                <div class="detail-section">
                    <h5>基本信息</h5>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <label>映射ID:</label>
                            <span>${mapping.id}</span>
                        </div>
                        <div class="detail-item">
                            <label>产品名称:</label>
                            <span>${mapping.product ? mapping.product.product_name : '-'}</span>
                        </div>
                        <div class="detail-item">
                            <label>提供商:</label>
                            <span>${mapping.provider ? mapping.provider.display_name : '-'}</span>
                        </div>
                        <div class="detail-item">
                            <label>上游产品代码:</label>
                            <span>${mapping.upstream_product_code}</span>
                        </div>
                        <div class="detail-item">
                            <label>价格倍数:</label>
                            <span>${mapping.price_multiplier}</span>
                        </div>
                        <div class="detail-item">
                            <label>状态:</label>
                            <span class="status ${mapping.is_active ? 'active' : 'inactive'}">
                                ${mapping.is_active ? '启用' : '停用'}
                            </span>
                        </div>
                        <div class="detail-item">
                            <label>创建时间:</label>
                            <span>${new Date(mapping.created_at).toLocaleString()}</span>
                        </div>
                        <div class="detail-item">
                            <label>更新时间:</label>
                            <span>${mapping.updated_at ? new Date(mapping.updated_at).toLocaleString() : '-'}</span>
                        </div>
                    </div>
                </div>
                ${mapping.upstream_params ? `
                <div class="detail-section">
                    <h5>API参数</h5>
                    <pre class="json-params">${JSON.stringify(mapping.upstream_params, null, 2)}</pre>
                </div>
                ` : ''}
            </div>
        `;
        
        modal.style.display = 'block';
    }

    async toggleMapping(mappingId) {
        try {
            this.showLoading();
            
            await api.put(`/admin/product-mappings/${mappingId}/toggle`);
            this.showToast('映射状态更新成功', 'success');
            this.loadProductMappings();
            
        } catch (error) {
            console.error('Failed to toggle mapping:', error);
            this.showToast('更新映射状态失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async deleteMapping(mappingId) {
        if (!confirm('确定要删除这个产品映射吗？此操作不可恢复。')) {
            return;
        }
        
        try {
            this.showLoading();
            
            await api.delete(`/admin/product-mappings/${mappingId}`);
            this.showToast('产品映射删除成功', 'success');
            this.loadProductMappings();
            
        } catch (error) {
            console.error('Failed to delete mapping:', error);
            this.showToast('删除产品映射失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // 提供商管理相关方法
    async loadProviders() {
        try {
            this.showLoading();
            
            const providers = await api.get('/admin/upstream-providers');
            this.renderProviders(providers);
        } catch (error) {
            console.error('Failed to load providers:', error);
            this.showToast('加载提供商列表失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    renderProviders(providers) {
        const tbody = document.getElementById('providersTableBody');
        
        if (providers.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center text-muted">
                        <i class="fas fa-server fa-2x mb-2"></i>
                        <p>暂无提供商</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = providers.map(provider => `
            <tr>
                <td>${provider.id}</td>
                <td>${provider.name}</td>
                <td>${provider.display_name}</td>
                <td>
                    <span class="badge badge-${this.getApiTypeBadgeClass(provider.api_type)}">
                        ${this.getApiTypeText(provider.api_type)}
                    </span>
                </td>
                <td>${provider.base_url}</td>
                <td>${provider.api_key_param || '-'}</td>
                <td>
                    <span class="status ${provider.is_active ? 'active' : 'inactive'}">
                        ${provider.is_active ? '启用' : '停用'}
                    </span>
                </td>
                <td>${new Date(provider.created_at).toLocaleString()}</td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline" onclick="window.adminPage.viewProvider(${provider.id})" title="查看详情">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="window.adminPage.editProvider(${provider.id})" title="编辑">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="window.adminPage.toggleProvider(${provider.id})" title="切换状态">
                            <i class="fas fa-${provider.is_active ? 'ban' : 'check'}"></i>
                        </button>
                        <button class="btn btn-sm btn-outline text-danger" onclick="window.adminPage.deleteProvider(${provider.id})" title="删除">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    getApiTypeBadgeClass(apiType) {
        const classMap = {
            'static': 'primary',
            'dynamic': 'success',
            'mobile': 'warning'
        };
        return classMap[apiType] || 'secondary';
    }

    getApiTypeText(apiType) {
        const textMap = {
            'static': '静态代理',
            'dynamic': '动态代理',
            'mobile': '移动代理'
        };
        return textMap[apiType] || apiType;
    }

    editProvider(providerId) {
        this.currentProviderId = providerId;
        
        if (providerId) {
            // 编辑模式 - 加载提供商数据
            this.loadProviderForEdit(providerId);
        } else {
            // 添加模式 - 清空表单
            this.clearProviderForm();
            document.getElementById('providerModalTitle').innerHTML = '<i class="fas fa-server"></i> 添加提供商';
            document.getElementById('providerModal').style.display = 'block';
        }
    }

    async loadProviderForEdit(providerId) {
        try {
            this.showLoading();
            
            const provider = await api.get(`/admin/upstream-providers/${providerId}`);
            
            // 填充表单
            document.getElementById('providerId').value = provider.id;
            document.getElementById('providerName').value = provider.name;
            document.getElementById('providerDisplayName').value = provider.display_name;
            document.getElementById('providerApiType').value = provider.api_type;
            document.getElementById('providerBaseUrl').value = provider.base_url;
            document.getElementById('providerApiKeyParam').value = provider.api_key_param || '';
            document.getElementById('providerApiKeyValue').value = provider.api_key_value || '';
            document.getElementById('providerConfig').value = provider.config ? JSON.stringify(provider.config, null, 2) : '';
            document.getElementById('providerIsActive').checked = provider.is_active;
            
            document.getElementById('providerModalTitle').innerHTML = '<i class="fas fa-edit"></i> 编辑提供商';
            document.getElementById('providerModal').style.display = 'block';
            
        } catch (error) {
            console.error('Failed to load provider for edit:', error);
            this.showToast('加载提供商信息失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    clearProviderForm() {
        document.getElementById('providerForm').reset();
        document.getElementById('providerId').value = '';
        document.getElementById('providerIsActive').checked = true;
    }

    async saveProvider() {
        const providerId = document.getElementById('providerId').value;
        const isEdit = !!providerId;
        
        let config = null;
        try {
            const configText = document.getElementById('providerConfig').value.trim();
            if (configText) {
                config = JSON.parse(configText);
            }
        } catch (error) {
            this.showToast('配置格式错误，请输入有效的JSON', 'error');
            return;
        }
        
        const providerData = {
            name: document.getElementById('providerName').value,
            display_name: document.getElementById('providerDisplayName').value,
            api_type: document.getElementById('providerApiType').value,
            base_url: document.getElementById('providerBaseUrl').value,
            api_key_param: document.getElementById('providerApiKeyParam').value || null,
            api_key_value: document.getElementById('providerApiKeyValue').value || null,
            config: config,
            is_active: document.getElementById('providerIsActive').checked
        };
        
        // 验证必填字段
        if (!providerData.name || !providerData.display_name || !providerData.api_type || !providerData.base_url) {
            this.showToast('请填写必填字段', 'error');
            return;
        }
        
        try {
            this.showLoading();
            
            if (isEdit) {
                await api.put(`/admin/upstream-providers/${providerId}`, providerData);
                this.showToast('提供商更新成功', 'success');
            } else {
                await api.post('/admin/upstream-providers', providerData);
                this.showToast('提供商添加成功', 'success');
            }
            
            this.closeModal('providerModal');
            this.loadProviders();
            
        } catch (error) {
            console.error('Failed to save provider:', error);
            this.showToast(isEdit ? '更新提供商失败' : '添加提供商失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async viewProvider(providerId) {
        try {
            this.showLoading();
            
            const provider = await api.get(`/admin/upstream-providers/${providerId}`);
            this.showProviderDetailModal(provider);
        } catch (error) {
            console.error('Failed to load provider:', error);
            this.showToast('加载提供商详情失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    showProviderDetailModal(provider) {
        const modal = document.getElementById('providerDetailModal');
        const modalBody = document.getElementById('providerDetailBody');
        
        modalBody.innerHTML = `
            <div class="provider-details">
                <div class="detail-section">
                    <h5>基本信息</h5>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <label>提供商ID:</label>
                            <span>${provider.id}</span>
                        </div>
                        <div class="detail-item">
                            <label>提供商名称:</label>
                            <span>${provider.name}</span>
                        </div>
                        <div class="detail-item">
                            <label>显示名称:</label>
                            <span>${provider.display_name}</span>
                        </div>
                        <div class="detail-item">
                            <label>API类型:</label>
                            <span class="badge badge-${this.getApiTypeBadgeClass(provider.api_type)}">
                                ${this.getApiTypeText(provider.api_type)}
                            </span>
                        </div>
                        <div class="detail-item">
                            <label>基础URL:</label>
                            <span>${provider.base_url}</span>
                        </div>
                        <div class="detail-item">
                            <label>API密钥参数:</label>
                            <span>${provider.api_key_param || '-'}</span>
                        </div>
                        <div class="detail-item">
                            <label>状态:</label>
                            <span class="status ${provider.is_active ? 'active' : 'inactive'}">
                                ${provider.is_active ? '启用' : '停用'}
                            </span>
                        </div>
                        <div class="detail-item">
                            <label>创建时间:</label>
                            <span>${new Date(provider.created_at).toLocaleString()}</span>
                        </div>
                        <div class="detail-item">
                            <label>更新时间:</label>
                            <span>${provider.updated_at ? new Date(provider.updated_at).toLocaleString() : '-'}</span>
                        </div>
                    </div>
                </div>
                ${provider.config ? `
                <div class="detail-section">
                    <h5>配置参数</h5>
                    <pre class="json-params">${JSON.stringify(provider.config, null, 2)}</pre>
                </div>
                ` : ''}
            </div>
        `;
        
        modal.style.display = 'block';
    }

    async toggleProvider(providerId) {
        try {
            this.showLoading();
            
            await api.put(`/admin/upstream-providers/${providerId}/toggle`);
            this.showToast('提供商状态更新成功', 'success');
            this.loadProviders();
            
        } catch (error) {
            console.error('Failed to toggle provider:', error);
            this.showToast('更新提供商状态失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async deleteProvider(providerId) {
        if (!confirm('确定要删除这个提供商吗？此操作不可恢复。')) {
            return;
        }
        
        try {
            this.showLoading();
            
            await api.delete(`/admin/upstream-providers/${providerId}`);
            this.showToast('提供商删除成功', 'success');
            this.loadProviders();
            
        } catch (error) {
            console.error('Failed to delete provider:', error);
            this.showToast('删除提供商失败', 'error');
        } finally {
            this.hideLoading();
        }
    }
}

// 全局变量
let adminPage;

// 导出AdminPage类到全局作用域
window.AdminPage = AdminPage;
