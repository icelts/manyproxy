class RechargePage {
    constructor() {
        this.selectedAmount = 0;
        this.currentPayment = null;
        this.paymentTimer = null;
        this.countdownTimer = null;
    }

    init() {
        this.bindEvents();
        this.loadUserInfo();
        this.loadSupportedCurrencies();
        this.loadRechargeHistory();
    }

    bindEvents() {
        document.querySelectorAll('.amount-btn').forEach((btn) => {
            btn.addEventListener('click', () => this.selectAmount(btn));
        });
        document.getElementById('customAmount').addEventListener('input', (e) => this.selectCustomAmount(e.target.value));
        document.getElementById('rechargeForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitRecharge();
        });
        document.getElementById('copyAddressBtn').addEventListener('click', () => this.copyAddress());
        document.getElementById('checkPaymentBtn').addEventListener('click', () => this.checkPaymentStatus());
        document.getElementById('cancelPaymentBtn').addEventListener('click', () => this.cancelPayment());
    }

    selectAmount(btn) {
        document.querySelectorAll('.amount-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        this.selectedAmount = parseFloat(btn.dataset.amount);
        document.getElementById('customAmount').value = '';
    }

    selectCustomAmount(amount) {
        if (amount && parseFloat(amount) > 0) {
            document.querySelectorAll('.amount-btn').forEach((b) => b.classList.remove('active'));
            this.selectedAmount = parseFloat(amount);
        }
    }

    async loadUserInfo() {
        try {
            await sessionController.initialized;
            let user = sessionController.getUser();
            if (!user) {
                const refreshed = await sessionController.refresh();
                user = refreshed?.user || null;
            }
            if (user) {
                const balance = Number(user.balance || 0);
                document.getElementById('userBalance').textContent = `$${balance.toFixed(2)}`;
            }
        } catch (error) {
            console.error('Failed to load user info:', error);
        }
    }

    async loadSupportedCurrencies() {
        try {
            const currencies = await api.get('/api/v1/orders/crypto/currencies');
            this.updateCurrencyOptions(currencies.currencies);
            this.updateExchangeRates(currencies.currencies);
        } catch (error) {
            console.error('Failed to load supported currencies:', error);
        }
    }

    updateCurrencyOptions(currencies) {
        const select = document.getElementById('cryptoCurrency');
        select.innerHTML = currencies.map((currency) => `
            <option value="${currency.code}">
                ${currency.name} (${currency.symbol})
            </option>
        `).join('');
    }

    updateExchangeRates(currencies) {
        const ratesContainer = document.getElementById('exchangeRates');
        ratesContainer.innerHTML = currencies.map((currency) => `
            <div class="d-flex justify-content-between border-bottom py-1">
                <span>${currency.code}</span>
                <strong>$${currency.rate.toFixed(2)}</strong>
            </div>
        `).join('');
    }

    async loadRechargeHistory() {
        try {
            const orders = await api.get('/api/v1/orders/', {
                params: {
                    order_type: 'recharge',
                    page: 1,
                    size: 5
                }
            });

            const historyHtml = orders.orders.map((order) => `
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div>
                        <div class="fw-bold">$${order.amount}</div>
                        <div class="text-muted small">${new Date(order.created_at).toLocaleString(i18n?.currentLang === 'en' ? 'en-US' : 'zh-CN')}</div>
                    </div>
                    <span class="badge ${order.status === 'completed' ? 'bg-success' : 'bg-warning text-dark'}">
                        ${this.getStatusText(order.status)}
                    </span>
                </div>
            `).join('');

            document.getElementById('rechargeHistory').innerHTML = historyHtml || `<p class="text-muted mb-0">${i18n?.t('recharge.historyEmpty') || '暂无充值记录'}</p>`;
        } catch (error) {
            console.error('Failed to load recharge history:', error);
            document.getElementById('rechargeHistory').innerHTML = '<p class="text-danger mb-0">加载失败</p>';
        }
    }

    getStatusText(status) {
        const map = {
            pending: i18n?.t('common.status.pending') || '待处理',
            paid: i18n?.t('common.status.paid') || '已支付',
            completed: i18n?.t('common.status.completed') || '已完成',
            cancelled: i18n?.t('common.status.cancelled') || '已取消',
            refunded: i18n?.t('common.status.refunded') || '已退款'
        };
        return map[status] || status;
    }

    async submitRecharge() {
        if (this.selectedAmount <= 0) {
            this.showToast(i18n?.t('recharge.toast.selectAmount') || '请选择充值金额', 'warning');
            return;
        }

        const cryptoCurrency = document.getElementById('cryptoCurrency').value;

        try {
            this.showLoading(i18n?.t('recharge.toast.creating') || '正在创建充值订单...');
            const response = await api.post('/api/v1/orders/recharge', {
                amount: this.selectedAmount,
                method: 'crypto',
                crypto_currency: cryptoCurrency
            });

            this.currentPayment = response;
            this.showPaymentInfo(response);
            this.startPaymentMonitoring();
            this.showToast(i18n?.t('recharge.toast.created') || '订单创建成功，请扫码支付', 'success');
        } catch (error) {
            console.error('Recharge failed:', error);
            this.showToast(error.message || i18n?.t('recharge.toast.failed') || '充值失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    showPaymentInfo(payment) {
        document.getElementById('paymentAmount').textContent = `$${payment.order.amount}`;
        document.getElementById('paymentAddress').value = payment.payment.wallet_address;
        document.getElementById('paymentCard').style.display = 'block';
        document.getElementById('paymentStatus').textContent = i18n?.t('common.status.pending') || '待处理';
        this.generateQRCode(payment.payment.wallet_address);
        this.startCountdown(payment.payment.expires_at);
    }

    generateQRCode(address) {
        const qrCodeDiv = document.getElementById('qrCode');
        qrCodeDiv.innerHTML = `
            <div class="border rounded p-3">
                <i class="fas fa-qrcode fa-4x mb-2"></i>
                <div class="small text-muted">${address}</div>
            </div>
        `;
    }

    startCountdown(expiresAt) {
        if (this.countdownTimer) clearInterval(this.countdownTimer);
        const expiresTime = new Date(expiresAt).getTime();

        this.countdownTimer = setInterval(() => {
            const now = Date.now();
            const distance = expiresTime - now;
            if (distance < 0) {
                clearInterval(this.countdownTimer);
                document.getElementById('remainingTime').textContent = '--:--';
                this.paymentExpired();
                return;
            }
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);
            document.getElementById('remainingTime').textContent =
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    startPaymentMonitoring() {
        if (this.paymentTimer) clearInterval(this.paymentTimer);
        this.paymentTimer = setInterval(() => this.checkPaymentStatus(), 10000);
    }

    async checkPaymentStatus() {
        if (!this.currentPayment) return;
        try {
            const payment = await api.get(`/api/v1/orders/payments/${this.currentPayment.payment.payment_id}`);
            document.getElementById('confirmations').textContent =
                `${payment.confirmations} / ${payment.required_confirmations}`;

            if (payment.status === 'confirmed') {
                this.paymentSuccess();
            } else if (payment.status === 'failed') {
                this.paymentFailed();
            }
        } catch (error) {
            console.error('Failed to check payment status:', error);
        }
    }

    paymentSuccess() {
        clearInterval(this.paymentTimer);
        clearInterval(this.countdownTimer);
        document.getElementById('paymentStatus').textContent = i18n?.t('common.status.completed') || '已完成';
        document.getElementById('paymentStatus').className = 'badge bg-success';
        this.showToast(i18n?.t('recharge.toast.success') || '充值成功！', 'success');
        this.loadUserInfo();
        this.loadRechargeHistory();
        setTimeout(() => {
            document.getElementById('paymentCard').style.display = 'none';
            this.currentPayment = null;
        }, 3000);
    }

    paymentFailed() {
        clearInterval(this.paymentTimer);
        clearInterval(this.countdownTimer);
        document.getElementById('paymentStatus').textContent = i18n?.t('common.status.failed') || '失败';
        document.getElementById('paymentStatus').className = 'badge bg-danger';
        this.showToast(i18n?.t('recharge.toast.failed') || '支付失败，请重试', 'error');
    }

    paymentExpired() {
        clearInterval(this.paymentTimer);
        document.getElementById('paymentStatus').textContent = i18n?.t('common.status.expired') || '已过期';
        document.getElementById('paymentStatus').className = 'badge bg-secondary';
        this.showToast(i18n?.t('recharge.toast.expired') || '支付已过期，请重新创建订单', 'warning');
    }

    cancelPayment() {
        clearInterval(this.paymentTimer);
        clearInterval(this.countdownTimer);
        document.getElementById('paymentCard').style.display = 'none';
        this.currentPayment = null;
        this.showToast(i18n?.t('recharge.toast.cancelled') || '支付已取消', 'info');
    }

    copyAddress() {
        const addressInput = document.getElementById('paymentAddress');
        addressInput.select();
        document.execCommand('copy');
        this.showToast(i18n?.t('recharge.toast.copy') || '地址已复制到剪贴板', 'success');
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');
        toast.className = 'toast';
        toast.classList.add(
            type === 'success' ? 'bg-success text-white' :
            type === 'error' ? 'bg-danger text-white' :
            type === 'warning' ? 'bg-warning text-dark' :
            'bg-info text-white'
        );
        toastMessage.textContent = message;
        new bootstrap.Toast(toast).show();
    }

    showLoading(message) {
        const overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner">
                <i class="fas fa-spinner fa-spin"></i>
                <p class="mb-0">${message}</p>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    hideLoading() {
        document.getElementById('loadingOverlay')?.remove();
    }
}

const rechargePage = new RechargePage();
window.rechargePage = rechargePage;
