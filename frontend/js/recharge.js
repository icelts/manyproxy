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
        this.supportedServices = [];
        this.currentService = null;
        this.currentPaymentLink = '';
        this.currentPaymentAmount = null;
        this.currentExpiresAt = null;
        this.paymentTimer = null;
        this.countdownTimer = null;
        this.paymentPollIntervalMs = 3000;
        this.paymentLinkAutoOpenAttempted = false;
        this.paymentLinkOpened = false;
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
        const currencySelect = document.getElementById('cryptoCurrency');
        if (currencySelect) {
            currencySelect.addEventListener('change', () => this.handleCurrencyChange());
        }
        const networkSelect = document.getElementById('cryptoNetwork');
        if (networkSelect) {
            networkSelect.addEventListener('change', () => this.updateServiceInfo());
        }
        document.getElementById('rechargeForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitRecharge();
        });
        document.getElementById('copyAddressBtn').addEventListener('click', () => this.copyAddress());
        document.getElementById('copyAmountBtn')?.addEventListener('click', () => this.copyAmount());
        document.getElementById('openPaymentLinkBtn')?.addEventListener('click', () => this.openPaymentLink());
        document.getElementById('copyPaymentLinkBtn')?.addEventListener('click', () => this.copyPaymentLink());
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

    async loadUserInfo(options = {}) {
        try {
            await sessionController.initialized;
            let user = sessionController.getUser();
            if (options.force) {
                const refreshed = await sessionController.refresh();
                user = refreshed?.user || user;
            } else if (!user) {
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
            const response = await api.get('/api/v1/orders/crypto/currencies');
            const services = response.currencies || [];
            this.supportedServices = services;
            this.updateCurrencyOptions(services);
            this.updateNetworkOptions();
            this.updateServiceInfo();
        } catch (error) {
            console.error('Failed to load supported currencies:', error);
        }
    }

    updateCurrencyOptions(services) {
        const select = document.getElementById('cryptoCurrency');
        if (!select) return;
        const currencyMap = new Map();
        services.forEach((service) => {
            const code = service.code;
            if (!code) return;
            if (!currencyMap.has(code)) {
                currencyMap.set(code, service);
            }
        });
        const placeholder = this.t('recharge.currencyPlaceholder', 'Select currency');
        const options = Array.from(currencyMap.values()).map((currency) => {
            const currencyLabel =
                currency.name && currency.symbol
                    ? `${currency.name} (${currency.symbol})`
                    : currency.code;
            return `<option value="${currency.code}">${currencyLabel}</option>`;
        }).join('');
        select.innerHTML = `<option value="">${placeholder}</option>${options}`;
        if (currencyMap.size === 1) {
            select.value = currencyMap.keys().next().value;
        }
    }

    handleCurrencyChange() {
        this.updateNetworkOptions();
        this.updateServiceInfo();
    }

    updateNetworkOptions() {
        const currencySelect = document.getElementById('cryptoCurrency');
        const networkSelect = document.getElementById('cryptoNetwork');
        if (!currencySelect || !networkSelect) return;
        const currency = currencySelect.value;
        const placeholder = this.t('recharge.networkPlaceholder', 'Select network');
        if (!currency) {
            networkSelect.innerHTML = `<option value="">${placeholder}</option>`;
            return;
        }
        const services = this.supportedServices.filter((service) => service.code === currency);
        if (services.length === 0) {
            networkSelect.innerHTML = `<option value="">${placeholder}</option>`;
            return;
        }
        const unavailableText = this.t('recharge.serviceUnavailable', 'Unavailable');
        const options = services.map((service) => {
            const networkCode = (service.network_code || service.network || '').toUpperCase();
            const label = service.network || networkCode || service.code;
            const disabled = service.available === false;
            const statusLabel = disabled ? ` (${unavailableText})` : '';
            return `<option value="${networkCode}" ${disabled ? 'disabled' : ''}>${label}${statusLabel}</option>`;
        }).join('');
        networkSelect.innerHTML = `<option value="">${placeholder}</option>${options}`;
        const defaultService = services.find((service) => service.available !== false) || services[0];
        if (defaultService) {
            networkSelect.value = (defaultService.network_code || defaultService.network || '').toUpperCase();
        }
    }

    getSelectedService() {
        const currency = document.getElementById('cryptoCurrency')?.value;
        const network = document.getElementById('cryptoNetwork')?.value;
        if (!currency || !network) return null;
        return this.supportedServices.find((service) => {
            const networkCode = (service.network_code || service.network || '').toUpperCase();
            return service.code === currency && networkCode === network.toUpperCase();
        }) || null;
    }

    updateServiceInfo() {
        const infoContainer = document.getElementById('serviceInfo');
        if (!infoContainer) return;
        const service = this.getSelectedService();
        this.currentService = service;
        if (!service) {
            infoContainer.innerHTML = `<p class="text-muted mb-0">${this.t('recharge.serviceEmpty', 'Select currency and network')}</p>`;
            return;
        }
        const limit = service.limit || {};
        const commission = service.commission || {};
        const availabilityText = service.available === false
            ? this.t('recharge.serviceUnavailable', 'Unavailable')
            : this.t('recharge.serviceAvailable', 'Available');
        const availabilityClass = service.available === false ? 'bg-secondary' : 'bg-success';
        const feePercent = commission.percent ? `${commission.percent}%` : '--';

        infoContainer.innerHTML = `
            <div class="d-flex justify-content-between border-bottom py-1">
                <span>${this.t('recharge.serviceStatus', 'Service')}</span>
                <span class="badge ${availabilityClass}">${availabilityText}</span>
            </div>
            <div class="d-flex justify-content-between border-bottom py-1">
                <span>${this.t('recharge.minAmount', 'Minimum')}</span>
                <strong>${this.formatServiceValue(limit.min_amount, service.code)}</strong>
            </div>
            <div class="d-flex justify-content-between border-bottom py-1">
                <span>${this.t('recharge.maxAmount', 'Maximum')}</span>
                <strong>${this.formatServiceValue(limit.max_amount, service.code)}</strong>
            </div>
            <div class="d-flex justify-content-between border-bottom py-1">
                <span>${this.t('recharge.feePercent', 'Fee Percent')}</span>
                <strong>${feePercent}</strong>
            </div>
            <div class="d-flex justify-content-between border-bottom py-1">
                <span>${this.t('recharge.feeAmount', 'Fee Amount')}</span>
                <strong>${this.formatServiceValue(commission.fee_amount, service.code)}</strong>
            </div>
            <div class="d-flex justify-content-between pt-1">
                <span>${this.t('recharge.confirmationsRequired', 'Confirmations')}</span>
                <strong>${service.confirmations ?? '--'}</strong>
            </div>
        `;
    }

    formatServiceValue(value, currency) {
        if (value === null || value === undefined || value === '') return '--';
        const text = typeof value === 'number' ? value.toString() : value;
        return currency ? `${text} ${currency}` : text;
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
                <div class="history-item">
                    <div class="history-info">
                        <div class="history-amount">$${order.amount}</div>
                        ${order.description ? `<div class="text-muted small">${escapeHTML(order.description)}</div>` : ''}
                        <div class="history-date">${new Date(order.created_at).toLocaleString(i18n?.currentLang === 'en' ? 'en-US' : 'zh-CN')}</div>
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

    updateStatusDisplay(status, rawStatus) {
        const badge = document.getElementById('paymentStatus');
        const detail = document.getElementById('paymentStatusDetail');
        if (!badge) return;
        const normalized = (status || '').toLowerCase();
        const statusMap = {
            pending: { key: 'common.status.pending', fallback: '待处理', className: 'badge bg-warning text-dark' },
            confirmed: { key: 'common.status.confirmed', fallback: '已确认', className: 'badge bg-success' },
            paid: { key: 'common.status.paid', fallback: '已支付', className: 'badge bg-success' },
            failed: { key: 'common.status.failed', fallback: '失败', className: 'badge bg-danger' },
            cancelled: { key: 'common.status.cancelled', fallback: '已取消', className: 'badge bg-secondary' },
            expired: { key: 'common.status.expired', fallback: '已过期', className: 'badge bg-secondary' }
        };
        const mapping = statusMap[normalized] || statusMap.pending;
        badge.textContent = this.t(mapping.key, mapping.fallback);
        badge.className = mapping.className;
        if (detail) {
            const statusDetail = this.getCryptomusStatusDetail(rawStatus);
            detail.textContent = statusDetail || '';
        }
    }

    getCryptomusStatusDetail(rawStatus) {
        if (!rawStatus) return '';
        const key = String(rawStatus).toLowerCase();
        const fallbackMap = {
            pending: 'Payment pending',
            confirmed: 'Payment confirmed',
            paid: 'Payment successful',
            paid_over: 'Payment successful (overpaid)',
            wrong_amount: 'Amount paid is less than required',
            process: 'Payment processing',
            confirm_check: 'Waiting for confirmations',
            wrong_amount_waiting: 'Underpaid, awaiting additional payment',
            check: 'Payment pending',
            fail: 'Payment failed',
            cancel: 'Payment cancelled',
            system_fail: 'System error',
            refund_process: 'Refund processing',
            refund_fail: 'Refund failed',
            refund_paid: 'Refund completed',
            locked: 'Funds locked (AML)',
            expired: 'Payment expired',
            wrong_currency: 'Wrong currency'
        };
        return this.t(`recharge.status.${key}`, fallbackMap[key] || rawStatus);
    }

    async submitRecharge() {
        if (this.selectedAmount <= 0) {
            this.showToast(i18n?.t('recharge.toast.selectAmount') || '请选择充值金额', 'warning');
            return;
        }

        const currencySelect = document.getElementById('cryptoCurrency');
        const networkSelect = document.getElementById('cryptoNetwork');
        const cryptoCurrency = currencySelect?.value;
        const cryptoNetwork = (networkSelect?.value || '').toUpperCase();

        if (!cryptoCurrency) {
            this.showToast(i18n?.t('recharge.toast.selectCurrency') || '请选择币种', 'warning');
            return;
        }

        const selectedService = this.getSelectedService();
        if (!cryptoNetwork || !selectedService) {
            this.showToast(i18n?.t('recharge.toast.selectNetwork') || '请选择网络', 'warning');
            return;
        }

        if (selectedService.available === false) {
            this.showToast(i18n?.t('recharge.toast.serviceUnavailable') || '当前网络不可用', 'warning');
            return;
        }

        const minRaw = selectedService.limit?.min_amount;
        const maxRaw = selectedService.limit?.max_amount;
        const minAmount = minRaw !== undefined && minRaw !== null ? Number(minRaw) : null;
        const maxAmount = maxRaw !== undefined && maxRaw !== null ? Number(maxRaw) : null;
        if (Number.isFinite(minAmount) && this.selectedAmount < minAmount) {
            const template = this.t('recharge.toast.minAmount', 'Minimum amount is {min} {currency}');
            const message = this.formatTemplate(template, {
                min: minRaw,
                currency: cryptoCurrency
            });
            this.showToast(message, 'warning');
            return;
        }
        if (Number.isFinite(maxAmount) && this.selectedAmount > maxAmount) {
            const template = this.t('recharge.toast.maxAmount', 'Maximum amount is {max} {currency}');
            const message = this.formatTemplate(template, {
                max: maxRaw,
                currency: cryptoCurrency
            });
            this.showToast(message, 'warning');
            return;
        }

        try {
            this.currentPaymentNetwork = selectedService.network || cryptoNetwork;
            this.showLoading(i18n?.t('recharge.toast.creating') || '正在创建充值订单...');
            const response = await api.post('/api/v1/orders/recharge', {
                amount: this.selectedAmount,
                method: 'crypto',
                crypto_currency: cryptoCurrency,
                crypto_network: cryptoNetwork
            });

            this.currentPayment = response;
            this.paymentLinkAutoOpenAttempted = false;
            this.paymentLinkOpened = false;
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
        const order = payment.order || {};
        const paymentInfo = payment.payment || {};
        const cryptoInfo = payment.crypto_payment || {};

        document.getElementById('paymentAmount').textContent = `$${order.amount}`;
        document.getElementById('paymentId').textContent =
            paymentInfo.payment_id || cryptoInfo.payment_id || '--';

        const cryptoAmount = cryptoInfo.payer_amount || cryptoInfo.crypto_amount || paymentInfo.crypto_amount;
        const cryptoCurrency = cryptoInfo.payer_currency || cryptoInfo.crypto_currency || paymentInfo.crypto_currency;
        this.currentPaymentAmount = { amount: cryptoAmount, currency: cryptoCurrency };
        const cryptoAmountInput = document.getElementById('paymentCryptoAmount');
        if (cryptoAmountInput) {
            cryptoAmountInput.value = cryptoAmount && cryptoCurrency
                ? `${cryptoAmount} ${cryptoCurrency}`
                : '--';
        }

        const paymentUrl = cryptoInfo.payment_url || paymentInfo.payment_url || '';
        this.currentPaymentLink = paymentUrl;
        const paymentLinkGroup = document.getElementById('paymentLinkGroup');
        const paymentLinkInput = document.getElementById('paymentLink');
        if (paymentLinkInput) {
            paymentLinkInput.value = paymentUrl;
        }
        if (paymentLinkGroup) {
            paymentLinkGroup.style.display = paymentUrl ? 'block' : 'none';
        }
        this.tryAutoOpenPaymentLink(paymentUrl);

        const address = cryptoInfo.wallet_address || paymentInfo.wallet_address || '';
        document.getElementById('paymentAddress').value = address;
        document.getElementById('paymentCard').style.display = 'block';
        this.updateStatusDisplay('pending', cryptoInfo.cryptomus_status || 'check');
        const confirmationsEl = document.getElementById('confirmations');
        const confirmations = paymentInfo.confirmations ?? cryptoInfo.confirmations ?? 0;
        const required = paymentInfo.required_confirmations ?? cryptoInfo.required_confirmations ?? 0;
        if (confirmationsEl) {
            confirmationsEl.textContent = required
                ? `${confirmations} / ${required}`
                : `${confirmations}`;
        }

        const paymentNetworkEl = document.getElementById('paymentNetwork');
        if (paymentNetworkEl) {
            paymentNetworkEl.textContent = cryptoInfo.network || this.currentPaymentNetwork || '--';
        }
        
        const qrData = payment.qr_code || cryptoInfo.address_qr_code || address;
        this.generateQRCode(qrData, address);
        
        const expiresAt =
            cryptoInfo.expires_at ||
            paymentInfo.expires_at ||
            new Date(Date.now() + 30 * 60 * 1000).toISOString();
        this.currentExpiresAt = expiresAt;
        this.startCountdown(expiresAt);
    }

    tryAutoOpenPaymentLink(link) {
        if (!link || this.paymentLinkAutoOpenAttempted) return;
        this.paymentLinkAutoOpenAttempted = true;
        const opened = window.open(link, '_blank', 'noopener');
        if (opened) {
            this.paymentLinkOpened = true;
        }
    }

    generateQRCode(qrData, address) {
        const qrCodeDiv = document.getElementById('qrCode');
        const normalizedQrData = typeof qrData === 'string' ? qrData.trim() : '';
        if (!normalizedQrData && !address) {
            qrCodeDiv.innerHTML = `<div class="text-muted">${this.t('recharge.qrUnavailable', 'Payment QR code will appear once the address is ready.')}</div>`;
            return;
        }
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
        this.checkPaymentStatus();
        this.paymentTimer = setInterval(() => this.checkPaymentStatus(), this.paymentPollIntervalMs);
    }

    applyPaymentStatus(statusData) {
        if (!statusData) return;
        const status = (statusData.status || 'pending').toLowerCase();
        const confirmations = statusData.confirmations ?? 0;
        const required = statusData.required_confirmations ?? statusData.requiredConfirmations ?? 0;
        const confirmationsEl = document.getElementById('confirmations');
        if (confirmationsEl) {
            confirmationsEl.textContent = required
                ? `${confirmations} / ${required}`
                : `${confirmations}`;
        }
        this.updateStatusDisplay(status, statusData.cryptomus_status || statusData.status);

        const paymentNetworkEl = document.getElementById('paymentNetwork');
        if (paymentNetworkEl && statusData.network) {
            paymentNetworkEl.textContent = statusData.network;
        }

        const addressInput = document.getElementById('paymentAddress');
        if (addressInput && statusData.wallet_address && addressInput.value !== statusData.wallet_address) {
            addressInput.value = statusData.wallet_address;
            this.generateQRCode(
                statusData.address_qr_code || statusData.wallet_address,
                statusData.wallet_address
            );
        }

        if (statusData.payment_url) {
            this.currentPaymentLink = statusData.payment_url;
            const paymentLinkGroup = document.getElementById('paymentLinkGroup');
            const paymentLinkInput = document.getElementById('paymentLink');
            if (paymentLinkInput) {
                paymentLinkInput.value = statusData.payment_url;
            }
            if (paymentLinkGroup) {
                paymentLinkGroup.style.display = 'block';
            }
            this.tryAutoOpenPaymentLink(statusData.payment_url);
        }

        const cryptoAmount = statusData.payer_amount || statusData.crypto_amount;
        const cryptoCurrency = statusData.payer_currency || statusData.crypto_currency;
        if (cryptoAmount && cryptoCurrency) {
            const cryptoAmountInput = document.getElementById('paymentCryptoAmount');
            if (cryptoAmountInput) {
                cryptoAmountInput.value = `${cryptoAmount} ${cryptoCurrency}`;
            }
            this.currentPaymentAmount = { amount: cryptoAmount, currency: cryptoCurrency };
        }

        if (statusData.expires_at && statusData.expires_at !== this.currentExpiresAt) {
            this.currentExpiresAt = statusData.expires_at;
            this.startCountdown(statusData.expires_at);
        }

        if (status === 'confirmed' || status === 'paid') {
            this.paymentSuccess();
        } else if (status === 'failed') {
            this.paymentFailed();
        } else if (status === 'expired') {
            this.paymentExpired();
        } else if (status === 'cancelled') {
            this.paymentCancelled();
        }
    }

    async checkPaymentStatus() {
        if (!this.currentPayment) return;
        try {
            const paymentId = this.currentPayment.payment?.payment_id;
            if (!paymentId) return;
            const statusData = await api.get(`/api/v1/orders/payments/${paymentId}/monitor`);
            this.applyPaymentStatus(statusData);
        } catch (error) {
            console.error('Failed to check payment status:', error);
        }
    }

    paymentSuccess() {
        clearInterval(this.paymentTimer);
        clearInterval(this.countdownTimer);
        this.updateStatusDisplay('confirmed', 'paid');
        this.showToast(i18n?.t('recharge.toast.success') || '充值成功！', 'success');
        this.loadUserInfo({ force: true });
        this.loadRechargeHistory();
        setTimeout(() => {
            document.getElementById('paymentCard').style.display = 'none';
            this.currentPayment = null;
        }, 3000);
    }

    paymentFailed() {
        clearInterval(this.paymentTimer);
        clearInterval(this.countdownTimer);
        this.updateStatusDisplay('failed', 'fail');
        this.showToast(i18n?.t('recharge.toast.failed') || '支付失败，请重试', 'error');
    }

    paymentExpired() {
        clearInterval(this.paymentTimer);
        this.updateStatusDisplay('expired', 'expired');
        this.showToast(i18n?.t('recharge.toast.expired') || '支付已过期，请重新创建订单', 'warning');
    }

    paymentCancelled() {
        clearInterval(this.paymentTimer);
        clearInterval(this.countdownTimer);
        this.updateStatusDisplay('cancelled', 'cancel');
        this.showToast(i18n?.t('recharge.toast.cancelled') || '支付已取消', 'info');
    }

    cancelPayment() {
        clearInterval(this.paymentTimer);
        clearInterval(this.countdownTimer);
        document.getElementById('paymentCard').style.display = 'none';
        this.currentPayment = null;
        this.currentPaymentLink = '';
        this.currentPaymentAmount = null;
        this.currentExpiresAt = null;
        this.showToast(i18n?.t('recharge.toast.cancelled') || '支付已取消', 'info');
    }

    copyAddress() {
        const addressInput = document.getElementById('paymentAddress');
        this.copyText(addressInput?.value, addressInput)
            .then((copied) => {
                if (copied) {
                    this.showToast(i18n?.t('recharge.toast.copy') || '地址已复制到剪贴板', 'success');
                }
            });
    }

    copyAmount() {
        const amount = this.currentPaymentAmount?.amount;
        if (!amount) {
            this.showToast(i18n?.t('recharge.toast.copyAmountEmpty') || '暂无可复制的金额', 'warning');
            return;
        }
        this.copyText(String(amount))
            .then((copied) => {
                if (copied) {
                    this.showToast(i18n?.t('recharge.toast.copyAmount') || '金额已复制到剪贴板', 'success');
                }
            });
    }

    copyPaymentLink() {
        const linkInput = document.getElementById('paymentLink');
        const link = linkInput?.value || this.currentPaymentLink;
        if (!link) {
            this.showToast(i18n?.t('recharge.toast.copyLinkEmpty') || '暂无可复制的支付链接', 'warning');
            return;
        }
        this.copyText(link, linkInput)
            .then((copied) => {
                if (copied) {
                    this.showToast(i18n?.t('recharge.toast.copyLink') || '支付链接已复制到剪贴板', 'success');
                }
            });
    }

    openPaymentLink() {
        const linkInput = document.getElementById('paymentLink');
        const link = linkInput?.value || this.currentPaymentLink;
        if (!link) {
            this.showToast(i18n?.t('recharge.toast.openLinkEmpty') || '暂无可打开的支付链接', 'warning');
            return;
        }
        window.open(link, '_blank', 'noopener');
    }

    async copyText(value, inputEl) {
        if (!value) return false;
        if (navigator?.clipboard?.writeText) {
            try {
                await navigator.clipboard.writeText(value);
                return true;
            } catch (error) {
                console.warn('Clipboard API failed, fallback to execCommand:', error);
            }
        }
        if (inputEl) {
            inputEl.focus();
            inputEl.select();
            try {
                return document.execCommand('copy');
            } catch (_) {
                return false;
            }
        }
        const temp = document.createElement('textarea');
        temp.value = value;
        temp.setAttribute('readonly', '');
        temp.style.position = 'absolute';
        temp.style.left = '-9999px';
        document.body.appendChild(temp);
        temp.select();
        const copied = document.execCommand('copy');
        document.body.removeChild(temp);
        return copied;
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

    formatTemplate(template, params) {
        if (!template) return '';
        return Object.keys(params || {}).reduce((text, key) => {
            const value = params[key];
            return text.replace(new RegExp(`\\{${key}\\}`, 'g'), value);
        }, template);
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
