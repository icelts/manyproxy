class RechargePage {
    constructor() {
        this.selectedAmount = 0;
        this.currentPayment = null;
        this.paymentTimer = null;
        this.countdownTimer = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadUserInfo();
        this.loadSupportedCurrencies();
        this.loadRechargeHistory();
    }

    bindEvents() {
        // 金额选择按钮
        document.querySelectorAll('.amount-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.selectAmount(e.target);
            });
        });

        // 自定义金额输入
        document.getElementById('customAmount').addEventListener('input', (e) => {
            this.selectCustomAmount(e.target.value);
        });

        // 充值表单提交
        document.getElementById('rechargeForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitRecharge();
        });

        // 复制地址按钮
        document.getElementById('copyAddressBtn').addEventListener('click', () => {
            this.copyAddress();
        });

        // 检查支付状态
        document.getElementById('checkPaymentBtn').addEventListener('click', () => {
            this.checkPaymentStatus();
        });

        // 取消支付
        document.getElementById('cancelPaymentBtn').addEventListener('click', () => {
            this.cancelPayment();
        });

        // 退出登录
        document.getElementById('logoutBtn').addEventListener('click', () => {
            sessionController.logout({ redirectTo: '../pages/login.html' });
        });
    }

    selectAmount(btn) {
        // 清除之前的选择
        document.querySelectorAll('.amount-btn').forEach(b => b.classList.remove('active'));
        
        // 设置当前选择
        btn.classList.add('active');
        this.selectedAmount = parseFloat(btn.dataset.amount);
        
        // 清空自定义金额
        document.getElementById('customAmount').value = '';
    }

    selectCustomAmount(amount) {
        if (amount && parseFloat(amount) > 0) {
            // 清除按钮选择
            document.querySelectorAll('.amount-btn').forEach(b => b.classList.remove('active'));
            this.selectedAmount = parseFloat(amount);
        }
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
        select.innerHTML = currencies.map(currency => `
            <option value="${currency.code}">
                ${currency.name} (${currency.symbol})
            </option>
        `).join('');
    }

    updateExchangeRates(currencies) {
        const ratesContainer = document.getElementById('exchangeRates');
        if (ratesContainer) {
            const ratesHtml = currencies.map(currency => `
                <div class="rate-item">
                    <span class="currency-name">${currency.code}</span>
                    <span class="currency-rate">$${currency.rate.toFixed(2)}</span>
                </div>
            `).join('');
            ratesContainer.innerHTML = ratesHtml;
        }
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

            const historyHtml = orders.orders.map(order => `
                <div class="history-item">
                    <div class="history-info">
                        <div class="history-amount">$${order.amount}</div>
                        <div class="history-date">${new Date(order.created_at).toLocaleString()}</div>
                    </div>
                    <div class="history-status">
                        <span class="status ${order.status}">${this.getStatusText(order.status)}</span>
                    </div>
                </div>
            `).join('');

            document.getElementById('rechargeHistory').innerHTML = historyHtml || '<p class="text-muted">暂无充值记录</p>';
        } catch (error) {
            console.error('Failed to load recharge history:', error);
            document.getElementById('rechargeHistory').innerHTML = '<p class="text-danger">加载失败</p>';
        }
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

    async submitRecharge() {
        if (this.selectedAmount <= 0) {
            this.showToast('请选择充值金额', 'error');
            return;
        }

        const cryptoCurrency = document.getElementById('cryptoCurrency').value;
        
        try {
            this.showLoading('正在创建充值订单...');
            
            const response = await api.post('/api/v1/orders/recharge', {
                amount: this.selectedAmount,
                method: 'crypto',
                crypto_currency: cryptoCurrency
            });

            this.currentPayment = response;
            this.showPaymentInfo(response);
            this.startPaymentMonitoring();
            
            this.showToast('订单创建成功，请扫码支付', 'success');
        } catch (error) {
            console.error('Recharge failed:', error);
            this.showToast(error.message || '充值失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    showPaymentInfo(payment) {
        document.getElementById('paymentAmount').textContent = `$${payment.order.amount}`;
        document.getElementById('paymentAddress').value = payment.payment.wallet_address;
        
        // 生成二维码
        this.generateQRCode(payment.payment.wallet_address);
        
        // 显示支付卡片
        document.getElementById('paymentCard').style.display = 'block';
        
        // 开始倒计时
        this.startCountdown(payment.payment.expires_at);
    }

    generateQRCode(address) {
        // 这里应该使用二维码库生成二维码
        // 为了演示，我们使用一个简单的占位符
        const qrCodeDiv = document.getElementById('qrCode');
        qrCodeDiv.innerHTML = `
            <div class="qr-placeholder">
                <i class="fas fa-qrcode fa-5x"></i>
                <p>扫码地址: ${address}</p>
            </div>
        `;
        
        // 实际项目中可以使用 qrcode.js 库
        // const qr = new QRCode(qrCodeDiv, {
        //     text: address,
        //     width: 200,
        //     height: 200
        // });
    }

    startCountdown(expiresAt) {
        if (this.countdownTimer) {
            clearInterval(this.countdownTimer);
        }

        const expiresTime = new Date(expiresAt).getTime();
        
        this.countdownTimer = setInterval(() => {
            const now = new Date().getTime();
            const distance = expiresTime - now;
            
            if (distance < 0) {
                clearInterval(this.countdownTimer);
                document.getElementById('remainingTime').textContent = '已过期';
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
        if (this.paymentTimer) {
            clearInterval(this.paymentTimer);
        }

        // 每10秒检查一次支付状态
        this.paymentTimer = setInterval(async () => {
            await this.checkPaymentStatus();
        }, 10000);
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
        
        document.getElementById('paymentStatus').textContent = '支付成功';
        document.getElementById('paymentStatus').className = 'status success';
        
        this.showToast('充值成功！', 'success');
        
        // 刷新用户信息和充值记录
        this.loadUserInfo();
        this.loadRechargeHistory();
        
        // 3秒后隐藏支付卡片
        setTimeout(() => {
            document.getElementById('paymentCard').style.display = 'none';
            this.currentPayment = null;
        }, 3000);
    }

    paymentFailed() {
        clearInterval(this.paymentTimer);
        clearInterval(this.countdownTimer);
        
        document.getElementById('paymentStatus').textContent = '支付失败';
        document.getElementById('paymentStatus').className = 'status error';
        
        this.showToast('支付失败，请重试', 'error');
    }

    paymentExpired() {
        clearInterval(this.paymentTimer);
        clearInterval(this.countdownTimer);
        
        document.getElementById('paymentStatus').textContent = '支付已过期';
        document.getElementById('paymentStatus').className = 'status error';
        
        this.showToast('支付已过期，请重新创建订单', 'error');
    }

    cancelPayment() {
        clearInterval(this.paymentTimer);
        clearInterval(this.countdownTimer);
        
        document.getElementById('paymentCard').style.display = 'none';
        this.currentPayment = null;
        
        this.showToast('支付已取消', 'info');
    }

    copyAddress() {
        const addressInput = document.getElementById('paymentAddress');
        addressInput.select();
        document.execCommand('copy');
        
        this.showToast('地址已复制到剪贴板', 'success');
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
        // 创建加载遮罩
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
let rechargePage;
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await sessionController.ensurePage('payments', { redirectTo: '../pages/login.html' });
    } catch (error) {
        console.warn('用户无法访问充值页面', error);
        return;
    }
    
    rechargePage = new RechargePage();
});
