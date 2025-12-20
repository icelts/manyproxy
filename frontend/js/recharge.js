function escapeHTML(value) {
    if (value === null || value === undefined) return '';
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
            case "'":
                return '&#39;';
            default:
                return char;
        }
    });
}

class RechargePage {
    constructor() {
        this.selectedAmount = 0;
        this.currentPayment = null;
        this.currentPaymentNetwork = '';
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
        select.innerHTML = currencies.map((currency) => {
            const networkName = currency.network_code || currency.network || '';
            const currencyLabel =
                currency.name && currency.symbol
                    ? `${currency.name} (${currency.symbol})`
                    : currency.code;
            const displayName = networkName
                ? `${currencyLabel} - ${networkName}`
                : currencyLabel;
            return `
                <option value="${currency.code}" data-network="${networkName}">
                    ${displayName}
                </option>
            `;
        }).join('');
    }

    updateExchangeRates(currencies) {
        const ratesContainer = document.getElementById('exchangeRates');
        if (currencies.length === 0) {
            ratesContainer.innerHTML = '<p class="text-muted mb-0">暂无可用的汇率信息</p>';
            return;
        }
        
        ratesContainer.innerHTML = currencies.map((currency) => {
            const networkName = currency.network_code || currency.network || '';
            const displayName = networkName
                ? `${currency.code} - ${networkName}`
                : currency.code;
            return `
                <div class="d-flex justify-content-between border-bottom py-1">
                    <span>${displayName}</span>
                    <strong>$${currency.rate.toFixed(2)}</strong>
                </div>
            `;
        }).join('');
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
                        ${order.description ? `<div class="text-muted small">${escapeHTML(order.description)}</div>` : ''}
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
            pending: this.t('common.status.pending', '待处理'),
            paid: this.t('common.status.paid', '已支付'),
            completed: this.t('common.status.completed', '已完成'),
            cancelled: this.t('common.status.cancelled', '已取消'),
            refunded: this.t('common.status.refunded', '已退款'),
            failed: this.t('common.status.failed', '失败'),
            expired: this.t('common.status.expired', '已过期'),
        };
        return map[status] || status;
    }

    async submitRecharge() {
        if (this.selectedAmount <= 0) {
            this.showToast(i18n?.t('recharge.toast.selectAmount') || '请选择充值金额', 'warning');
            return;
        }

        const select = document.getElementById('cryptoCurrency');
        const cryptoCurrency = select.value;
        const cryptoNetworkRaw = select.selectedOptions[0]?.dataset.network || '';
        const cryptoNetwork = cryptoNetworkRaw.toUpperCase();

        if (!cryptoNetwork) {
            this.showToast(i18n?.t('recharge.toast.selectNetwork') || '请选择网络', 'warning');
            return;
        }

        try {
            this.currentPaymentNetwork = cryptoNetwork;
            this.showLoading(i18n?.t('recharge.toast.creating') || '正在创建充值订单...');
            const response = await api.post('/api/v1/orders/recharge', {
                amount: this.selectedAmount,
                method: 'crypto',
                crypto_currency: cryptoCurrency,
                crypto_network: cryptoNetwork
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
        document.getElementById('paymentStatus').textContent = this.t('common.status.pending', '待处理');

        const paymentNetworkEl = document.getElementById('paymentNetwork');
        if (paymentNetworkEl) {
            paymentNetworkEl.textContent = this.currentPaymentNetwork || '--';
        }
        
        const qrData = payment.qr_code || payment.payment.wallet_address;
        this.generateQRCode(qrData, payment.payment.wallet_address);
        
        const expiresAt =
            payment.payment.expires_at ||
            new Date(Date.now() + 30 * 60 * 1000).toISOString();
        this.startCountdown(expiresAt);
    }

    generateQRCode(qrData, address) {
        const qrCodeDiv = document.getElementById('qrCode');
        const normalizedQrData = typeof qrData === 'string' ? qrData.trim() : '';
        const isImageData =
            typeof normalizedQrData === 'string' &&
            normalizedQrData.startsWith('data:image');
        const looksLikePngBase64 =
            typeof normalizedQrData === 'string' &&
            normalizedQrData.startsWith('iVBOR') &&
            /^[A-Za-z0-9+/=]+$/.test(normalizedQrData);
        const qrUrl = isImageData
            ? normalizedQrData
            : looksLikePngBase64
                ? `data:image/png;base64,${normalizedQrData}`
                : `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(normalizedQrData || address || '')}`;
        const displayAddr = address || qrData;
        const fallbackData = address || normalizedQrData || '';
        const fallbackUrl = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(fallbackData)}`;

        qrCodeDiv.innerHTML = `
            <div class="border rounded p-3 text-center">
                <img src="${qrUrl}" alt="QR Code" class="mb-2"
                     style="width:220px;height:220px;max-width:100%;object-fit:contain;display:block;margin:0 auto;"
                     onerror="this.onerror=null; this.src='${fallbackUrl}';" />
                <div class="small text-muted">${displayAddr}</div>
            </div>
        `;
    }

    startCountdown(expiresAt) {
        if (this.countdownTimer) clearInterval(this.countdownTimer);
        
        // 默认30分钟过期时间
        let expiresTime = Date.now() + 30 * 60 * 1000;
        
        console.log('原始过期时间:', expiresAt);
        
        if (expiresAt) {
            try {
                // 处理不同格式的时间
                if (typeof expiresAt === 'string') {
                    const trimmed = expiresAt.trim();
                    // 数字字符串时间戳（秒/毫秒）
                    if (/^\d+$/.test(trimmed)) {
                        const numeric = Number(trimmed);
                        expiresTime = numeric < 2e12 ? numeric * 1000 : numeric;
                    } else {
                        // ISO 字符串：后端常返回无时区的 UTC 字符串，需要按 UTC 解析
                        const truncated = trimmed.replace(/(\.\d{3})\d+/, '$1');
                        const hasTimezone = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(truncated);
                        const normalized = hasTimezone ? truncated : `${truncated}Z`;
                        const parsed = Date.parse(normalized);
                    if (!isNaN(parsed)) {
                        expiresTime = parsed;
                    }
                    }
                } else if (typeof expiresAt === 'number') {
                    // 时间戳格式（可能是秒或毫秒）
                    expiresTime = expiresAt < 2e12 ? expiresAt * 1000 : expiresAt;
                }
            } catch (error) {
                console.error('解析过期时间失败:', error);
                expiresTime = Date.now() + 30 * 60 * 1000;
            }
        }

        console.log('解析后的过期时间:', new Date(expiresTime));
        console.log('当前时间:', new Date());

        // 立即更新一次显示
        const updateDisplay = () => {
            const now = Date.now();
            const distance = expiresTime - now;
            
            if (distance < 0) {
                clearInterval(this.countdownTimer);
                document.getElementById('remainingTime').textContent = '00:00';
                console.log('支付已过期');
                this.paymentExpired();
                return;
            }
            
            const totalSeconds = Math.floor(distance / 1000);
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds % 60;
            
            const displayText = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            document.getElementById('remainingTime').textContent = displayText;
            
            console.log(`剩余时间: ${displayText} (${distance}ms)`);
        };

        // 立即更新一次
        updateDisplay();
        
        // 每秒更新
        this.countdownTimer = setInterval(updateDisplay, 1000);
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
        document.getElementById('paymentStatus').textContent = this.t('common.status.completed', '已完成');
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
        document.getElementById('paymentStatus').textContent = this.t('common.status.failed', '失败');
        document.getElementById('paymentStatus').className = 'badge bg-danger';
        this.showToast(i18n?.t('recharge.toast.failed') || '支付失败，请重试', 'error');
    }

    paymentExpired() {
        clearInterval(this.paymentTimer);
        document.getElementById('paymentStatus').textContent = this.t('common.status.expired', '已过期');
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
        const classes =
            type === 'success' ? ['bg-success', 'text-white'] :
            type === 'error' ? ['bg-danger', 'text-white'] :
            type === 'warning' ? ['bg-warning', 'text-dark'] :
            ['bg-info', 'text-white'];
        toast.classList.add(...classes);
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

    t(key, fallback) {
        try {
            const translated = window.i18n?.t?.(key);
            return translated && translated !== key ? translated : fallback;
        } catch (_) {
            return fallback;
        }
    }
}

const rechargePage = new RechargePage();
window.rechargePage = rechargePage;
