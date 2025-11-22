class OrdersPage {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalOrders = 0;
        this.filters = {
            order_type: '',
            status: '',
            date_from: '',
            date_to: ''
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadUserInfo();
        this.loadOrders();
    }

    bindEvents() {
        // 筛选按钮
        document.getElementById('filterBtn').addEventListener('click', () => {
            this.applyFilters();
        });

        // 重置按钮
        document.getElementById('resetBtn').addEventListener('click', () => {
            this.resetFilters();
        });

        // 导出按钮
        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportOrders();
        });

        // 退出登录
        document.getElementById('logoutBtn').addEventListener('click', () => {
            sessionController.logout({ redirectTo: '../pages/login.html' });
        });

        // 模态框关闭按钮
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
    }

    async loadUserInfo() {
        try {
            await sessionController.initialized;
            let userInfo = sessionController.getUser();
            if (!userInfo) {
                const refreshed = await sessionController.refresh();
                userInfo = refreshed?.user || null;
            }

            if (userInfo) {
                const balance = Number(userInfo.balance || 0);
                document.getElementById('userBalance').textContent = `$${balance.toFixed(2)}`;
            }
        } catch (error) {
            console.error('Failed to load user info:', error);
        }
    }

    async loadOrders() {
        try {
            this.showLoading();
            
            const params = {
                page: this.currentPage,
                size: this.pageSize,
                ...this.filters
            };

            // 移除空值
            Object.keys(params).forEach(key => {
                if (!params[key]) delete params[key];
            });

            const response = await api.get('/api/v1/orders/', { params });
            
            this.totalOrders = response.total;
            this.renderOrders(response.orders);
            this.renderPagination();
            
            document.getElementById('totalOrders').textContent = this.totalOrders;
        } catch (error) {
            console.error('Failed to load orders:', error);
            this.showToast('加载订单失败', 'error');
            this.renderEmptyState();
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
                        <i class="fas fa-inbox fa-2x mb-2"></i>
                        <p>暂无订单</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = orders.map(order => `
            <tr>
                <td>
                    <span class="order-number">${order.order_number}</span>
                </td>
                <td>
                    <span class="badge badge-${this.getTypeClass(order.type)}">
                        ${this.getTypeText(order.type)}
                    </span>
                </td>
                <td>
                    <span class="amount">$${order.amount}</span>
                </td>
                <td>
                    <span class="status ${order.status}">
                        ${this.getStatusText(order.status)}
                    </span>
                </td>
                <td>
                    <span class="date">${new Date(order.created_at).toLocaleString()}</span>
                </td>
                <td>
                    <span class="description" title="${order.description || ''}">
                        ${order.description || '-'}
                    </span>
                </td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline" onclick="ordersPage.viewOrder(${order.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${order.type === 'recharge' ? `
                            <button class="btn btn-sm btn-outline" onclick="ordersPage.viewPayment(${order.id})">
                                <i class="fas fa-credit-card"></i>
                            </button>
                        ` : ''}
                        ${order.status === 'pending' ? `
                            <button class="btn btn-sm btn-danger" onclick="ordersPage.cancelOrder(${order.id})">
                                <i class="fas fa-times"></i>
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `).join('');
    }

    renderPagination() {
        const totalPages = Math.ceil(this.totalOrders / this.pageSize);
        const pagination = document.getElementById('pagination');
        
        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        let html = '';
        
        // 上一页
        html += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="ordersPage.goToPage(${this.currentPage - 1})">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;

        // 页码
        const startPage = Math.max(1, this.currentPage - 2);
        const endPage = Math.min(totalPages, this.currentPage + 2);

        if (startPage > 1) {
            html += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="ordersPage.goToPage(1)">1</a>
                </li>
            `;
            if (startPage > 2) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `
                <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="ordersPage.goToPage(${i})">${i}</a>
                </li>
            `;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            html += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="ordersPage.goToPage(${totalPages})">${totalPages}</a>
                </li>
            `;
        }

        // 下一页
        html += `
            <li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="ordersPage.goToPage(${this.currentPage + 1})">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;

        pagination.innerHTML = html;
    }

    goToPage(page) {
        if (page < 1 || page > Math.ceil(this.totalOrders / this.pageSize)) return;
        
        this.currentPage = page;
        this.loadOrders();
    }

    applyFilters() {
        this.filters = {
            order_type: document.getElementById('orderType').value,
            status: document.getElementById('orderStatus').value,
            date_from: document.getElementById('dateFrom').value,
            date_to: document.getElementById('dateTo').value
        };
        
        this.currentPage = 1;
        this.loadOrders();
    }

    resetFilters() {
        document.getElementById('orderType').value = '';
        document.getElementById('orderStatus').value = '';
        document.getElementById('dateFrom').value = '';
        document.getElementById('dateTo').value = '';
        
        this.filters = {
            order_type: '',
            status: '',
            date_from: '',
            date_to: ''
        };
        
        this.currentPage = 1;
        this.loadOrders();
    }

    async exportOrders() {
        try {
            this.showLoading('正在导出订单...');
            
            const params = {
                ...this.filters,
                export: true
            };

            // 移除空值
            Object.keys(params).forEach(key => {
                if (!params[key]) delete params[key];
            });

            const response = await api.get('/api/v1/orders/', { params });
            
            // 创建CSV内容
            const csv = this.convertToCSV(response.orders);
            this.downloadCSV(csv, `orders_${new Date().toISOString().split('T')[0]}.csv`);
            
            this.showToast('订单导出成功', 'success');
        } catch (error) {
            console.error('Failed to export orders:', error);
            this.showToast('导出失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    convertToCSV(orders) {
        const headers = ['订单号', '类型', '金额', '状态', '创建时间', '描述'];
        const rows = orders.map(order => [
            order.order_number,
            this.getTypeText(order.type),
            order.amount,
            this.getStatusText(order.status),
            new Date(order.created_at).toLocaleString(),
            order.description || ''
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        return '\ufeff' + csvContent; // 添加BOM以支持中文
    }

    downloadCSV(csv, filename) {
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    async viewOrder(orderId) {
        try {
            this.showLoading();
            
            const order = await api.get(`/api/v1/orders/${orderId}`);
            this.showOrderModal(order);
        } catch (error) {
            console.error('Failed to load order:', error);
            this.showToast('加载订单详情失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async viewPayment(orderId) {
        try {
            this.showLoading();
            
            // 获取订单的支付信息
            const orders = await api.get('/api/v1/orders/', {
                params: { page: 1, size: 1, order_id: orderId }
            });
            
            if (orders.orders.length > 0) {
                const order = orders.orders[0];
                // 这里需要根据实际的API结构调整
                this.showToast('支付详情功能开发中', 'info');
            }
        } catch (error) {
            console.error('Failed to load payment:', error);
            this.showToast('加载支付详情失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async cancelOrder(orderId) {
        if (!confirm('确定要取消这个订单吗？')) return;

        try {
            this.showLoading();
            
            // 这里需要实现取消订单的API
            // await api.put(`/api/v1/orders/${orderId}/cancel`);
            
            this.showToast('订单取消功能开发中', 'info');
            this.loadOrders();
        } catch (error) {
            console.error('Failed to cancel order:', error);
            this.showToast('取消订单失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    showOrderModal(order) {
        const modal = document.getElementById('orderModal');
        const modalBody = document.getElementById('orderModalBody');
        
        modalBody.innerHTML = `
            <div class="order-details">
                <div class="detail-section">
                    <h5>基本信息</h5>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <label>订单号:</label>
                            <span>${order.order_number}</span>
                        </div>
                        <div class="detail-item">
                            <label>订单类型:</label>
                            <span class="badge badge-${this.getTypeClass(order.type)}">
                                ${this.getTypeText(order.type)}
                            </span>
                        </div>
                        <div class="detail-item">
                            <label>订单金额:</label>
                            <span class="amount">$${order.amount}</span>
                        </div>
                        <div class="detail-item">
                            <label>订单状态:</label>
                            <span class="status ${order.status}">
                                ${this.getStatusText(order.status)}
                            </span>
                        </div>
                        <div class="detail-item">
                            <label>创建时间:</label>
                            <span>${new Date(order.created_at).toLocaleString()}</span>
                        </div>
                        <div class="detail-item">
                            <label>更新时间:</label>
                            <span>${order.updated_at ? new Date(order.updated_at).toLocaleString() : '-'}</span>
                        </div>
                    </div>
                </div>
                
                ${order.description ? `
                    <div class="detail-section">
                        <h5>订单描述</h5>
                        <p>${order.description}</p>
                    </div>
                ` : ''}
                
                <div class="detail-section">
                    <h5>时间线</h5>
                    <div class="timeline">
                        <div class="timeline-item">
                            <div class="timeline-dot created"></div>
                            <div class="timeline-content">
                                <div class="timeline-title">订单创建</div>
                                <div class="timeline-time">${new Date(order.created_at).toLocaleString()}</div>
                            </div>
                        </div>
                        ${order.paid_at ? `
                            <div class="timeline-item">
                                <div class="timeline-dot paid"></div>
                                <div class="timeline-content">
                                    <div class="timeline-title">订单支付</div>
                                    <div class="timeline-time">${new Date(order.paid_at).toLocaleString()}</div>
                                </div>
                            </div>
                        ` : ''}
                        ${order.completed_at ? `
                            <div class="timeline-item">
                                <div class="timeline-dot completed"></div>
                                <div class="timeline-content">
                                    <div class="timeline-title">订单完成</div>
                                    <div class="timeline-time">${new Date(order.completed_at).toLocaleString()}</div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
        
        modal.style.display = 'block';
    }

    getTypeText(type) {
        const typeMap = {
            'purchase': '购买订单',
            'recharge': '充值订单'
        };
        return typeMap[type] || type;
    }

    getTypeClass(type) {
        const classMap = {
            'purchase': 'primary',
            'recharge': 'success'
        };
        return classMap[type] || 'secondary';
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

    renderEmptyState() {
        const tbody = document.getElementById('ordersTableBody');
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    <i class="fas fa-inbox fa-3x mb-3"></i>
                    <p>暂无订单数据</p>
                </td>
            </tr>
        `;
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
}

// 初始化页面
let ordersPage;
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await sessionController.ensurePage('orders', { redirectTo: '../pages/login.html' });
    } catch (error) {
        console.warn('用户无法访问订单页面', error);
        return;
    }

    ordersPage = new OrdersPage();
});
