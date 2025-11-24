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
    }

    init() {
        this.bindEvents();
        this.loadOrders();
    }

    bindEvents() {
        document.getElementById('filterBtn').addEventListener('click', () => this.applyFilters());
        document.getElementById('resetBtn').addEventListener('click', () => this.resetFilters());
        document.getElementById('exportBtn').addEventListener('click', () => this.exportOrders());

        document.querySelectorAll('.close').forEach((btn) => {
            btn.addEventListener('click', () => {
                document.getElementById(btn.dataset.close).style.display = 'none';
            });
        });

        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.style.display = 'none';
            }
        });
    }

    async loadOrders() {
        try {
            this.showLoading();
            const params = {
                page: this.currentPage,
                size: this.pageSize,
                ...this.filters
            };
            Object.keys(params).forEach((key) => {
                if (!params[key]) delete params[key];
            });

            const response = await api.get('/api/v1/orders/', { params });
            this.totalOrders = response.total;
            this.renderOrders(response.orders);
            this.renderPagination();
            document.getElementById('ordersTotalLabel').textContent =
                i18n?.t('orders.total', { count: this.totalOrders }) || `共 ${this.totalOrders} 个订单`;
        } catch (error) {
            console.error('Failed to load orders:', error);
            this.showToast(i18n?.t('orders.toast.loadFailed') || '加载订单失败', 'error');
            this.renderEmptyState();
        } finally {
            this.hideLoading();
        }
    }

    renderOrders(orders) {
        const tbody = document.getElementById('ordersTableBody');
        if (!orders.length) {
            this.renderEmptyState();
            return;
        }

        tbody.innerHTML = orders.map((order) => `
            <tr>
                <td>${order.order_number}</td>
                <td><span class="badge badge-${order.type}">${this.getTypeText(order.type)}</span></td>
                <td>$${order.amount}</td>
                <td><span class="status ${order.status}">${this.getStatusText(order.status)}</span></td>
                <td>${new Date(order.created_at).toLocaleString(i18n?.currentLang === 'en' ? 'en-US' : 'zh-CN')}</td>
                <td title="${order.description || ''}">${order.description || '-'}</td>
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
        html += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="ordersPage.goToPage(${this.currentPage - 1})">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;

        const startPage = Math.max(1, this.currentPage - 2);
        const endPage = Math.min(totalPages, this.currentPage + 2);

        for (let i = startPage; i <= endPage; i += 1) {
            html += `
                <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="ordersPage.goToPage(${i})">${i}</a>
                </li>
            `;
        }

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
        const totalPages = Math.ceil(this.totalOrders / this.pageSize);
        if (page < 1 || page > totalPages) return;
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
            this.showLoading(i18n?.t('orders.toast.exporting') || '正在导出订单...');
            const params = { ...this.filters, export: true };
            Object.keys(params).forEach((key) => {
                if (!params[key]) delete params[key];
            });
            const response = await api.get('/api/v1/orders/', { params });
            const csv = this.convertToCSV(response.orders);
            this.downloadCSV(csv, `orders_${new Date().toISOString().split('T')[0]}.csv`);
            this.showToast(i18n?.t('orders.toast.exportSuccess') || '订单导出成功', 'success');
        } catch (error) {
            console.error('Failed to export orders:', error);
            this.showToast(i18n?.t('orders.toast.exportFailed') || '导出失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    convertToCSV(orders) {
        const headers = [
            i18n?.t('orders.table.number') || '订单号',
            i18n?.t('orders.table.type') || '类型',
            i18n?.t('orders.table.amount') || '金额',
            i18n?.t('orders.table.status') || '状态',
            i18n?.t('orders.table.created') || '创建时间',
            i18n?.t('orders.table.description') || '描述'
        ];

        const rows = orders.map((order) => [
            order.order_number,
            this.getTypeText(order.type),
            order.amount,
            this.getStatusText(order.status),
            new Date(order.created_at).toLocaleString(),
            order.description || ''
        ]);

        return [
            headers.join(','),
            ...rows.map((row) => row.map((cell) => `"${cell}"`).join(','))
        ].join('\n');
    }

    downloadCSV(csv, filename) {
        const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
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
            this.showToast(i18n?.t('orders.toast.detailFailed') || '加载订单详情失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async viewPayment(orderId) {
        this.showToast(i18n?.t('orders.toast.paymentInfo') || '支付详情功能开发中', 'info');
    }

    cancelOrder(orderId) {
        const confirmMessage = i18n?.t('orders.toast.cancelConfirm') || '确定要取消这个订单吗？';
        if (!confirm(confirmMessage)) return;
        this.showToast(i18n?.t('orders.toast.cancelUnsupported') || '取消订单功能开发中', 'info');
    }

    showOrderModal(order) {
        const modal = document.getElementById('orderModal');
        const modalBody = document.getElementById('orderModalBody');
        modalBody.innerHTML = `
            <div class="order-details">
                <h5>${i18n?.t('orders.detail.basic') || '基本信息'}</h5>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>${i18n?.t('orders.detail.number') || '订单号'}</label>
                        <span>${order.order_number}</span>
                    </div>
                    <div class="detail-item">
                        <label>${i18n?.t('orders.detail.type') || '订单类型'}</label>
                        <span>${this.getTypeText(order.type)}</span>
                    </div>
                    <div class="detail-item">
                        <label>${i18n?.t('orders.detail.amount') || '订单金额'}</label>
                        <span>$${order.amount}</span>
                    </div>
                    <div class="detail-item">
                        <label>${i18n?.t('orders.detail.status') || '订单状态'}</label>
                        <span>${this.getStatusText(order.status)}</span>
                    </div>
                    <div class="detail-item">
                        <label>${i18n?.t('orders.detail.created') || '创建时间'}</label>
                        <span>${new Date(order.created_at).toLocaleString()}</span>
                    </div>
                    <div class="detail-item">
                        <label>${i18n?.t('orders.detail.updated') || '更新时间'}</label>
                        <span>${order.updated_at ? new Date(order.updated_at).toLocaleString() : '-'}</span>
                    </div>
                </div>
                ${order.description ? `<div class="mt-3">${order.description}</div>` : ''}
                <h5 class="mt-4">${i18n?.t('orders.detail.timeline') || '时间线'}</h5>
                <div class="timeline">
                    <div class="timeline-item">
                        <div class="timeline-dot created"></div>
                        <div class="timeline-content">
                            <div class="timeline-title">${i18n?.t('orders.detail.createdEvent') || '订单创建'}</div>
                            <div class="timeline-time">${new Date(order.created_at).toLocaleString()}</div>
                        </div>
                    </div>
                    ${order.paid_at ? `
                        <div class="timeline-item">
                            <div class="timeline-dot paid"></div>
                            <div class="timeline-content">
                                <div class="timeline-title">${i18n?.t('orders.detail.paidEvent') || '订单支付'}</div>
                                <div class="timeline-time">${new Date(order.paid_at).toLocaleString()}</div>
                            </div>
                        </div>
                    ` : ''}
                    ${order.completed_at ? `
                        <div class="timeline-item">
                            <div class="timeline-dot completed"></div>
                            <div class="timeline-content">
                                <div class="timeline-title">${i18n?.t('orders.detail.completedEvent') || '订单完成'}</div>
                                <div class="timeline-time">${new Date(order.completed_at).toLocaleString()}</div>
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        modal.style.display = 'block';
    }

    getTypeText(type) {
        const map = {
            purchase: i18n?.t('orders.filters.purchase') || '购买订单',
            recharge: i18n?.t('orders.filters.recharge') || '充值订单'
        };
        return map[type] || type;
    }

    getStatusText(status) {
        const map = {
            pending: i18n?.t('orders.filters.pending') || '待支付',
            paid: i18n?.t('orders.filters.paid') || '已支付',
            completed: i18n?.t('orders.filters.completed') || '已完成',
            cancelled: i18n?.t('orders.filters.cancelled') || '已取消',
            refunded: i18n?.t('orders.filters.refunded') || '已退款'
        };
        return map[status] || status;
    }

    renderEmptyState() {
        document.getElementById('ordersTableBody').innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    <i class="fas fa-inbox fa-3x mb-3"></i>
                    <p>${i18n?.t('orders.empty') || '暂无订单'}</p>
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

    showLoading(message = i18n?.t('common.loading') || '加载中...') {
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
        document.getElementById('loadingOverlay')?.remove();
    }
}

const ordersPage = new OrdersPage();
window.ordersPage = ordersPage;
