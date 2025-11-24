class ProductsPage {
    constructor() {
        this.products = [];
    }

    async init() {
        try {
            await sessionController.initialized;
            await this.updateBalance();
            await this.loadProducts();
        } catch (error) {
            console.error('初始化产品页面失败:', error);
        }
    }

    async updateBalance() {
        try {
            const user = sessionController.getUser() || await api.getUserInfo();
            document.getElementById('user-balance').textContent = Number(user.balance || 0).toFixed(2);
        } catch (error) {
            console.error('获取余额失败:', error);
        }
    }

    async loadProducts() {
        try {
            const response = await api.get('/proxy/products');
            this.products = response;
            this.displayProducts();
        } catch (error) {
            console.error('加载产品失败:', error);
            this.showToast(i18n?.t('products.toast.loadFailed') || '加载产品失败，请稍后重试', 'error');
            ['static', 'dynamic', 'mobile'].forEach((category) => {
                const container = document.getElementById(`${category}-products`);
                if (container) {
                    container.innerHTML = `<div class="col-12 text-center text-muted">${i18n?.t('common.noData') || '暂无数据'}</div>`;
                }
            });
        }
    }

    displayProducts() {
        ['static', 'dynamic', 'mobile'].forEach((category) => {
            const container = document.getElementById(`${category}-products`);
            if (!container) return;

            const categoryProducts = this.products.filter((p) => p.category === category);
            if (categoryProducts.length === 0) {
                container.innerHTML = `
                    <div class="col-12 text-center text-muted">
                        ${i18n?.t('products.emptyCategory', { category: this.getCategoryName(category) }) || '暂无产品'}
                    </div>
                `;
                return;
            }

            container.innerHTML = categoryProducts.map((product) => this.createProductCard(product)).join('');
        });
    }

    createProductCard(product) {
        return `
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 shadow-sm">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="card-title mb-0">${product.product_name}</h5>
                            <span class="badge bg-primary">${this.getCategoryName(product.category)}</span>
                        </div>
                        <span class="h5 text-primary mb-0">$${Number(product.price).toFixed(2)}</span>
                    </div>
                    <div class="card-body">
                        <p class="card-text">${product.description || ''}</p>
                        <ul class="list-unstyled small text-muted">
                            <li><i class="fas fa-server me-2"></i>${i18n?.t('products.labels.provider') || '提供商'}: ${product.provider}</li>
                            <li><i class="fas fa-clock me-2"></i>${i18n?.t('products.labels.duration') || '时长'}: ${this.formatDuration(product.duration_days)}</li>
                        </ul>
                        <div class="input-group">
                            <span class="input-group-text" data-i18n="products.quantity">${i18n?.t('products.quantity') || '数量'}</span>
                            <input type="number" class="form-control" id="quantity-${product.id}" min="1" value="1" max="100">
                            <span class="input-group-text" data-i18n="products.unit">${i18n?.t('products.unit') || '个'}</span>
                        </div>
                    </div>
                    <div class="card-footer bg-white border-top-0">
                        <button class="btn btn-primary w-100" onclick="productManager.purchaseProduct(${product.id})">
                            <i class="fas fa-shopping-cart me-1"></i>${i18n?.t('common.buttons.buy') || '购买'}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    getCategoryName(category) {
        switch (category) {
            case 'static':
                return i18n?.t('proxy.labels.static') || '静态代理';
            case 'dynamic':
                return i18n?.t('proxy.labels.dynamic') || '动态代理';
            case 'mobile':
                return i18n?.t('proxy.labels.mobile') || '移动代理';
            default:
                return category;
        }
    }

    formatDuration(days) {
        if (!days) return '-';
        return i18n?.currentLang === 'en' ? `${days} days` : `${days} 天`;
    }

    purchaseProduct(productId) {
        const product = this.products.find((p) => p.id === productId);
        if (!product) return;

        const quantityInput = document.getElementById(`quantity-${productId}`);
        const quantity = parseInt(quantityInput?.value, 10) || 1;

        if (quantity < 1 || quantity > 100) {
            this.showToast(i18n?.t('products.toast.invalidQuantity') || '购买数量必须在 1-100 之间', 'warning');
            return;
        }

        const totalPrice = (product.price * quantity).toFixed(2);
        document.getElementById('purchase-details').innerHTML = `
            <h6>${product.product_name}</h6>
            <p class="text-muted">${product.description || ''}</p>
            <ul class="list-unstyled small mb-3">
                <li><strong>${i18n?.t('products.labels.provider') || '提供商'}:</strong> ${product.provider}</li>
                <li><strong>${i18n?.t('products.labels.price') || '单价'}:</strong> $${product.price}</li>
            </ul>
            <ul class="list-unstyled small mb-0">
                <li><strong>${i18n?.t('products.labels.quantity') || '数量'}:</strong> ${quantity}</li>
                <li><strong>${i18n?.t('products.labels.total') || '总价'}:</strong> $${totalPrice}</li>
                <li><strong>${i18n?.t('products.labels.duration') || '时长'}:</strong> ${this.formatDuration(product.duration_days)}</li>
            </ul>
            <p class="text-warning mt-3 mb-0">${i18n?.t('products.balanceWarning', { amount: `$${totalPrice}` }) || `请确认余额充足（需要 $${totalPrice}）`}</p>
        `;

        const modal = new bootstrap.Modal(document.getElementById('confirmPurchaseModal'));
        document.getElementById('confirm-purchase-btn').onclick = () => this.confirmPurchase(product, quantity, modal);
        modal.show();
    }

    async confirmPurchase(product, quantity, modal) {
        try {
            if (product.category === 'static') {
                await api.post('/proxy/static/buy', {
                    provider: product.provider.toLowerCase(),
                    quantity,
                    protocol: 'http',
                    username: 'user',
                    password: 'pass'
                });
            } else if (product.category === 'dynamic') {
                await api.post('/proxy/dynamic/buy', {
                    duration_days: product.duration_days,
                    quantity
                });
            } else if (product.category === 'mobile') {
                if (quantity > 1) {
                    this.showToast(i18n?.t('products.toast.invalidQuantity') || '购买数量必须在 1-100 之间', 'warning');
                    return;
                }
                await api.post('/proxy/mobile/buy', { package_id: product.id });
            }

            this.showToast(i18n?.t('products.toast.creationSuccess') || '成功创建购买，订单正在处理中', 'success');
            await this.updateBalance();
            modal.hide();
        } catch (error) {
            console.error('购买产品失败:', error);
            this.showToast(error.message || i18n?.t('products.toast.createFailed') || '购买失败，请稍后重试', 'error');
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
        new bootstrap.Toast(toastEl).show();
    }
}

const productManager = new ProductsPage();
window.productManager = productManager;
