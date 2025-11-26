const STATIC_PROVIDER_OPTIONS = ['Viettel', 'FPT', 'VNPT'];

class ProductsPage {
    constructor() {
        this.products = [];
        this.staticDefaults = null;
        this.purchaseCompleted = false;
        this.virtualProducts = {};
    }

    async init() {
        try {
            await sessionController.initialized;
            await this.updateBalance();
            await this.loadProducts();
        } catch (error) {
            console.error('初始化产品页面失败', error);
        }
    }

    async updateBalance() {
        try {
            // 强制从服务器获取最新的用户信息，不使用缓存
            const user = await api.getUserInfo();
            
            // 更新sessionController的缓存
            if (sessionController.state && sessionController.state.user) {
                sessionController.state.user.balance = user.balance;
                sessionController.storage.setItem(sessionController.sessionKey, JSON.stringify(sessionController.state));
                sessionController.emitChange();
            }
            
            // 更新页面显示
            document.getElementById('user-balance').textContent = Number(user.balance || 0).toFixed(2);
        } catch (error) {
            console.error('获取余额失败:', error);
            // 如果获取失败，尝试使用缓存的数据
            const cachedUser = sessionController.getUser();
            if (cachedUser) {
                document.getElementById('user-balance').textContent = Number(cachedUser.balance || 0).toFixed(2);
            }
        }
    }

    async loadProducts() {
        try {
            const response = await api.get('/proxy/products');
            this.products = response;
            this.displayProducts();
        } catch (error) {
            if (this.handleApiKeyError(error, true)) {
                return;
            }
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
        const grouped = { static: [], dynamic: [], mobile: [] };

        this.products.forEach((product) => {
            const normalized = (product.category || '').toLowerCase();
            if (grouped[normalized]) {
                grouped[normalized].push(product);
            }
        });

        ['static', 'dynamic', 'mobile'].forEach((category) => {
            const container = document.getElementById(`${category}-products`);
            if (!container) return;

            const categoryProducts = grouped[category] || [];

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
        const priceLabel = `$${Number(product.price || 0).toFixed(2)}`;

        const detailList = `
            <ul class="list-unstyled small text-muted">
                <li><i class="fas fa-server me-2"></i>${i18n?.t('products.labels.provider') || '提供商'}: ${product.provider}</li>
                <li><i class="fas fa-clock me-2"></i>${i18n?.t('products.labels.duration') || '时长'}: ${this.formatDuration(product.duration_days)}</li>
            </ul>
        `;

        const quantityBlock = `
                        <div class="input-group">
                            <span class="input-group-text" data-i18n="products.quantity">${i18n?.t('products.quantity') || '数量'}</span>
                            <input type="number" class="form-control" id="quantity-${product.id}" min="1" value="1" max="100">
                            <span class="input-group-text" data-i18n="products.unit">${i18n?.t('products.unit') || '个'}</span>
                        </div>
        `;
        const buttonHandler = `productManager.purchaseProduct('${product.id}')`;

        return `
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 shadow-sm">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="card-title mb-0">${product.product_name}</h5>
                            <span class="badge bg-primary">${this.getCategoryName(product.category)}</span>
                        </div>
                        <span class="h5 text-primary mb-0">${priceLabel}</span>
                    </div>
                    <div class="card-body">
                        <p class="card-text">${product.description || ''}</p>
                        ${detailList}
                        ${quantityBlock}
                    </div>
                    <div class="card-footer bg-white border-top-0">
                        <button class="btn btn-primary w-100" onclick="${buttonHandler}">
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

    formatStaticHeaderPrice(product) {
        const durations = this.getStaticDurations(product);
        const first = durations[0];
        if (!first) {
            return i18n?.t('products.static.noPricing') || '未配置价格';
        }
        const prefix = i18n?.currentLang === 'en' ? 'From' : '套餐起';
        return `${prefix} $${first.price.toFixed(2)}`;
    }

    buildStaticPricingList(product) {
        const durations = this.getStaticDurations(product);
        if (!durations.length) {
            return `<p class="text-danger small">${i18n?.t('products.static.noPricing') || '尚未配置套餐价格'}</p>`;
        }
        const rows = durations.map((item) => `
            <li><i class="fas fa-clock me-2"></i>${item.days}${i18n?.currentLang === 'en' ? ' days' : ' 天'} - $${item.price.toFixed(2)}</li>
        `).join('');
        const providerLabel = product.virtual
            ? (i18n?.t('products.static.operator') || '选择运营商')
            : product.provider;
        return `
            <ul class="list-unstyled small text-muted">
                <li><i class="fas fa-server me-2"></i>${i18n?.t('products.labels.provider') || '提供商'}: ${providerLabel}</li>
                ${rows}
            </ul>
        `;
    }

    purchaseProduct(productId) {
        const key = String(productId);
        const product = this.products.find((p) => String(p.id) === key);
        if (!product) return;

        if (!api.hasApiKey()) {
            this.showToast(i18n?.t('common.apiKeyRequired') || '请先创建 API Key 才能执行该操作', 'warning');
            return;
        }

        const quantityInput = document.getElementById(`quantity-${key}`);
        const quantity = parseInt(quantityInput?.value, 10) || 1;

        if (quantity < 1 || quantity > 100) {
            this.showToast(i18n?.t('products.toast.invalidQuantity') || '购买数量必须在 1-100 之间', 'warning');
            return;
        }

        this.purchaseCompleted = false;
        this.resetConfirmButton();

        const unitPrice = Number(product.price || 0);
        const durationDays = product.duration_days;

        const modalBody = document.getElementById('purchase-details');
        modalBody.innerHTML = `
            ${this.buildPurchaseOverview(product, quantity, unitPrice, durationDays)}
            ${product.category === 'static' ? this.buildStaticPurchaseForm(product) : ''}
            <div id="purchase-result" class="alert d-none mt-3" role="alert"></div>
        `;
        this.clearPurchaseResult();

        const modal = new bootstrap.Modal(document.getElementById('confirmPurchaseModal'));
        document.getElementById('confirm-purchase-btn').onclick = () => this.confirmPurchase(product, quantity, modal);
        modal.show();
    }

    async purchaseStaticInline(virtualProduct, quantity) {
        if (!api.hasApiKey()) {
            this.showToast(i18n?.t('common.apiKeyRequired') || '请先创建 API Key 才能执行该操作', 'warning');
            return;
        }
        const providerKey = this.getSelectedStaticProviderKey(virtualProduct.id);
        const providerData = this.getVirtualProviderData(virtualProduct, providerKey);
        if (!providerData) {
            this.showToast(i18n?.t('products.static.selectProvider') || '请选择运营商', 'warning');
            return;
        }

        const durationSelect = document.getElementById(`static-duration-${virtualProduct.id}`);
        const duration = parseInt(durationSelect?.value, 10);
        if (!duration || duration <= 0) {
            this.showToast(i18n?.t('products.toast.selectDuration') || '请选择有效的套餐时长', 'warning');
            return;
        }

        try {
            const providerOverride = providerData.overrideProvider || providerData.product.provider;
            const inlineValues = {
                duration,
                protocol: 'HTTP',
                username: 'random',
                password: 'random',
                providerOverride
            };
            await this.submitStaticPurchase(providerData.product, quantity, inlineValues, { inline: true });
            await this.updateBalance();
        } catch (error) {
            if (this.handleApiKeyError(error)) {
                return;
            }
            console.error('Inline static purchase failed:', error);
            const message = error?.response?.detail || error?.message || i18n?.t('products.toast.createFailed') || '购买失败，请稍后重试';
            this.showToast(message, 'error');
        }
    }

    async confirmPurchase(product, quantity, modal) {
        try {
            if (product.category === 'static') {
                if (this.purchaseCompleted) {
                    return;
                }
                await this.submitStaticPurchase(product, quantity);
                await this.updateBalance();
                this.purchaseCompleted = true;
                this.disableConfirmButton();
                return;
            } else if (product.category === 'dynamic') {
                await api.post('/proxy/dynamic/buy', {
                    product_id: product.id,
                    quantity
                });
            } else if (product.category === 'mobile') {
                if (quantity > 1) {
                    this.showToast(i18n?.t('products.toast.invalidQuantity') || '购买数量必须在 1-100 之间', 'warning');
                    return;
                }
                const upstreamPackage = product.package_id || product.upstream_package || product.id;
                await api.post('/proxy/mobile/buy', {
                    product_id: product.id,
                    package_id: upstreamPackage,
                    quantity
                });
            }

            this.showToast(i18n?.t('products.toast.creationSuccess') || '成功创建购买，订单正在处理中', 'success');
            await this.updateBalance();
            modal.hide();
        } catch (error) {
            if (this.handleApiKeyError(error)) {
                modal.hide();
                return;
            }
            console.error('购买产品失败:', error);
            const message = error.response?.detail || error.message || i18n?.t('products.toast.createFailed') || '购买失败，请稍后重试';
            this.showToast(message, 'error');
            this.showPurchaseResult(false, `<strong>${i18n?.t('products.result.errorTitle') || '请求失败'}</strong><br>${message}`);
        }
    }

    async submitStaticPurchase(product, quantity, inlineValues = null) {
        const formValues = inlineValues || this.readStaticFormValues();
        const unitPrice = Number(product.price || 0);
        const durationDays = product.duration_days || 30;
        
        const providerOverride = inlineValues?.providerOverride;
        const payload = {
            product_id: product.id,
            provider: providerOverride || product.provider,
            quantity,
            protocol: formValues.protocol,
            username: formValues.username,
            password: formValues.password
        };

        const order = await api.post('/proxy/static/buy', payload);
        this.showToast(i18n?.t('products.toast.creationSuccess') || '购买请求创建成功，正在处理中', 'success');
        if (!inlineValues) {
            this.renderStaticPurchaseResult(order, product, formValues, unitPrice, quantity);
        }
    }

    buildPurchaseOverview(product, quantity, unitPrice, durationDays) {
        const totalPrice = (unitPrice * quantity).toFixed(2);
        return `
            <h6>${product.product_name}</h6>
            <p class="text-muted">${product.description || ''}</p>
            <ul class="list-unstyled small mb-3">
                <li><strong>${i18n?.t('products.labels.provider') || '提供商'}:</strong> ${product.provider}</li>
                <li><strong>${i18n?.t('products.labels.price') || '单价'}:</strong> $${Number(unitPrice || 0).toFixed(2)}</li>
            </ul>
            <ul class="list-unstyled small mb-0">
                <li><strong>${i18n?.t('products.labels.quantity') || '数量'}:</strong> ${quantity}</li>
                <li><strong>${i18n?.t('products.labels.total') || '总价'}:</strong> $${totalPrice}</li>
                <li><strong>${i18n?.t('products.labels.duration') || '时长'}:</strong> ${this.formatDuration(durationDays)}</li>
            </ul>
            <p class="text-warning mt-3 mb-3">${i18n?.t('products.balanceWarning', { amount: `$${totalPrice}` }) || `请确认余额充足（需要 $${totalPrice}）`}</p>
        `;
    }

    buildStaticDefaults(product, durations = this.getStaticDurations(product)) {
        const fallback = durations.length ? durations[0].days : 30;
        return {
            protocol: 'HTTP',
            username: this.generateCredential('user'),
            password: this.generateCredential('pass'),
            duration: fallback
        };
    }

    buildStaticPurchaseForm(product) {
        const defaults = {
            protocol: 'HTTP',
            username: this.generateCredential('user'),
            password: this.generateCredential('pass')
        };
        
        return `
            <div class="card border-0 bg-light mb-3">
                <div class="card-body">
                    <h6 class="fw-semibold mb-3">${i18n?.t('products.form.title') || '配置静态代理参数'}</h6>
                    <div class="row g-3">
                        <div class="col-md-4">
                            <label class="form-label">${i18n?.t('products.form.protocol') || '协议'}</label>
                            <select class="form-select" id="static-protocol">
                                <option value="HTTP"${defaults.protocol === 'HTTP' ? ' selected' : ''}>HTTP</option>
                                <option value="SOCKS5"${defaults.protocol === 'SOCKS5' ? ' selected' : ''}>SOCKS5</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">${i18n?.t('products.form.username') || '用户名'}</label>
                            <input type="text" class="form-control" id="static-username" value="${defaults.username}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">${i18n?.t('products.form.password') || '密码'}</label>
                            <input type="text" class="form-control" id="static-password" value="${defaults.password}">
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    readStaticFormValues() {
        const defaults = {
            protocol: 'HTTP',
            username: this.generateCredential('user'),
            password: this.generateCredential('pass')
        };
        
        const protocol = document.getElementById('static-protocol')?.value || defaults.protocol;
        const username = document.getElementById('static-username')?.value?.trim() || defaults.username;
        const password = document.getElementById('static-password')?.value?.trim() || defaults.password;

        return { protocol, username, password };
    }

    renderStaticPurchaseResult(order, product, formValues, unitPrice, quantity) {
        const info = order.proxy_info || {};
        const provider = info.loaiproxy || product.provider;
        const proxyLine = info.proxy || `${info.ip || '-'}:${info.port || ''}`;
        const expiresAt = order.expires_at || (info.time ? new Date(info.time * 1000).toISOString() : null);
        const totalPrice = (unitPrice * quantity).toFixed(2);
        const rows = [
            { label: i18n?.t('products.result.orderId') || '订单号', value: order.order_id },
            { label: i18n?.t('products.result.upstreamId') || '上游ID', value: order.upstream_id || info.idproxy || '-' },
            { label: i18n?.t('products.result.provider') || '供应商', value: provider },
            { label: i18n?.t('products.result.username') || '用户名', value: info.user || formValues.username },
            { label: i18n?.t('products.result.password') || '密码', value: info.password || formValues.password },
            { label: i18n?.t('products.labels.quantity') || '数量', value: quantity },
            { label: i18n?.t('products.result.unitPrice') || '单价', value: `$${Number(unitPrice || 0).toFixed(2)}` },
            { label: i18n?.t('products.result.total') || '总价', value: `$${totalPrice}` },
            { label: i18n?.t('products.result.proxy') || '代理', value: proxyLine },
            { label: i18n?.t('products.result.expires') || '到期时间', value: this.formatDateTime(expiresAt) }
        ];

        const details = `
            <div class="mb-2">
                <strong>${i18n?.t('products.result.title') || '购买成功'}</strong>
            </div>
            <p class="small text-muted mb-3">${i18n?.t('products.result.copyTip') || '请立即复制下方信息并妥善保管。'}</p>
            <dl class="row mb-0">
                ${rows.map((row) => `
                    <dt class="col-sm-4">${row.label}</dt>
                    <dd class="col-sm-8 text-break">${row.value || '-'}</dd>
                `).join('')}
            </dl>
        `;
        this.showPurchaseResult(true, details);
    }

    formatDateTime(value) {
        if (!value) return '-';
        try {
            const date = new Date(value);
            return date.toLocaleString(i18n?.currentLang === 'en' ? 'en-US' : 'zh-CN', { hour12: false });
        } catch {
            return value;
        }
    }

    showPurchaseResult(success, html) {
        const container = document.getElementById('purchase-result');
        if (!container) return;
        container.className = `alert mt-3 ${success ? 'alert-success' : 'alert-danger'}`;
        container.innerHTML = html;
        container.classList.remove('d-none');
    }

    clearPurchaseResult() {
        const container = document.getElementById('purchase-result');
        if (container) {
            container.className = 'alert d-none mt-3';
            container.innerHTML = '';
        }
    }

    generateCredential(prefix = 'user') {
        return `${prefix}-${Math.random().toString(36).slice(-6)}`;
    }

    getStaticDurations(product) {
        if (product?.virtual && product.virtualOptions) {
            const defaultProvider = product.virtualOptions.defaultProvider;
            const providerData = this.getVirtualProviderData(product, defaultProvider);
            if (providerData?.durations?.length) {
                return providerData.durations;
            }
        }
        const durations = [];
        
        // 动态获取所有价格字段，支持任意时长
        const priceFields = Object.keys(product).filter(key => 
            key.startsWith('price_') && key !== 'price'
        );
        
        priceFields.forEach(field => {
            const days = parseInt(field.replace('price_', ''), 10);
            const price = product[field];
            if (days > 0 && price !== null && price !== undefined) {
                durations.push({ days, price: Number(price) });
            }
        });
        
        // 如果没有找到 price_XX 字段，使用基础 price 字段和 duration_days
        if (durations.length === 0 && product.price !== null && product.price !== undefined) {
            const basePrice = Number(product.price);
            const duration = product.duration_days || 30;
            durations.push({ days: duration, price: basePrice });
        }
        
        // 按天数排序
        durations.sort((a, b) => a.days - b.days);
        
        return durations;
    }

    getStaticPrice(product, days) {
        const durations = this.getStaticDurations(product);
        const entry = durations.find((item) => item.days === days);
        return entry ? entry.price : null;
    }

    buildVirtualStaticProduct(products) {
        if (!products.length) {
            return null;
        }

        // 获取所有非通用产品作为基础数据源
        const nonGeneric = products.filter((product) => {
            const provider = (product.provider || '').toLowerCase();
            return provider && provider !== 'generic' && provider !== '*';
        });

        // 使用第一个产品作为模板，但为所有三个提供商创建选项
        const templateProduct = nonGeneric.length ? nonGeneric[0] : products[0];
        const templateDurations = this.getStaticDurations(templateProduct);
        
        if (!templateDurations.length) {
            return null;
        }

        // 为所有三个提供商创建选项
        const entries = STATIC_PROVIDER_OPTIONS.map((name) => {
            // 找到对应提供商的实际产品，如果没有则使用模板
            const actualProduct = nonGeneric.find(p => p.provider === name) || templateProduct;
            const durations = this.getStaticDurations(actualProduct);
            
            return {
                provider: name,
                label: name,
                product: actualProduct,
                durations: durations.length ? durations : templateDurations,
                overrideProvider: name
            };
        }).filter(Boolean);

        if (!entries.length) {
            return null;
        }

        const base = templateProduct;
        const providerMap = entries.reduce((map, entry) => {
            map[entry.provider] = entry;
            return map;
        }, {});

        return {
            id: 'static-inline',
            category: 'static',
            subcategory: base.subcategory,
            provider: base.provider,
            product_name: i18n?.t('products.static.inlineTitle') || '静态代理',
            description: i18n?.t('products.static.inlineDescription') || '支持多个运营商的静态代理服务',
            price_30: base.price_30,
            price_60: base.price_60,
            price_90: base.price_90,
            duration_days: base.duration_days,
            virtual: true,
            virtualOptions: {
                defaultProvider: 'Viettel', // 默认选择Viettel
                providers: entries,
                providerMap
            }
        };
    }

    renderStaticInlineControls(product) {
        const options = product.virtualOptions;
        if (!options) return '';
        const providerOptions = options.providers.map((item) => `
            <option value="${item.provider}"${item.provider === options.defaultProvider ? ' selected' : ''}>${item.label}</option>
        `).join('');
        const durationOptions = this.buildStaticDurationOptions(product, options.defaultProvider);
        const protocols = i18n?.t('products.static.protocols') || 'HTTPS & SOCKS5';

        return `
            <div class="border rounded p-3 bg-light mb-3">
                <div class="row g-3 align-items-end">
                    <div class="col-md-6">
                        <label class="form-label">${i18n?.t('products.static.operator') || '选择运营商'}</label>
                        <select class="form-select" id="static-provider-${product.id}" onchange="productManager.onStaticProviderChange('${product.id}')">
                            ${providerOptions}
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">${i18n?.t('products.form.duration') || '套餐时长'}</label>
                        <select class="form-select" id="static-duration-${product.id}" onchange="productManager.onStaticDurationChange('${product.id}')">
                            ${durationOptions}
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">${i18n?.t('products.quantity') || '数量'}</label>
                        <input type="number" class="form-control" id="quantity-${product.id}" min="1" value="1" max="100">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">${i18n?.t('products.static.protocolHint') || '协议'}</label>
                        <div class="form-control-plaintext fw-semibold text-primary">${protocols}</div>
                    </div>
                </div>
                <div class="mt-3 small text-muted" id="static-price-${product.id}">
                    ${this.renderStaticPriceSummary(product, options.defaultProvider)}
                </div>
            </div>
        `;
    }

    buildStaticDurationOptions(product, providerKey) {
        const providerData = this.getVirtualProviderData(product, providerKey);
        if (!providerData) return '';
        return providerData.durations.map((item, index) => `
            <option value="${item.days}"${index === 0 ? ' selected' : ''}>${item.days}${i18n?.currentLang === 'en' ? ' days' : ' 天'} · $${item.price.toFixed(2)}</option>
        `).join('');
    }

    renderStaticPriceSummary(product, providerKey, duration = null) {
        const providerData = this.getVirtualProviderData(product, providerKey);
        if (!providerData) return '';
        const targetDuration = duration || providerData.durations[0]?.days;
        const selected = providerData.durations.find((item) => item.days === targetDuration) || providerData.durations[0];
        if (!selected) return '';
        return i18n?.t('products.static.selectionSummary', {
            provider: providerData.label,
            days: selected.days,
            price: selected.price.toFixed(2)
        }) || `${providerData.label} · ${selected.days}${i18n?.currentLang === 'en' ? ' days' : ' 天'} · $${selected.price.toFixed(2)}`;
    }

    onStaticProviderChange(productId) {
        const virtualProduct = this.virtualProducts[productId];
        if (!virtualProduct?.virtualOptions) return;
        const providerKey = this.getSelectedStaticProviderKey(productId);
        const durationSelect = document.getElementById(`static-duration-${productId}`);
        if (durationSelect) {
            durationSelect.innerHTML = this.buildStaticDurationOptions(virtualProduct, providerKey);
        }
        this.onStaticDurationChange(productId);
    }

    onStaticDurationChange(productId) {
        const virtualProduct = this.virtualProducts[productId];
        if (!virtualProduct) return;
        const providerKey = this.getSelectedStaticProviderKey(productId);
        const durationSelect = document.getElementById(`static-duration-${productId}`);
        const duration = parseInt(durationSelect?.value, 10);
        const label = document.getElementById(`static-price-${productId}`);
        if (label) {
            label.innerHTML = this.renderStaticPriceSummary(virtualProduct, providerKey, duration);
        }
    }

    getSelectedStaticProviderKey(productId) {
        const virtualProduct = this.virtualProducts[productId];
        if (!virtualProduct?.virtualOptions) return null;
        const select = document.getElementById(`static-provider-${productId}`);
        return select?.value || virtualProduct.virtualOptions.defaultProvider;
    }

    getVirtualProviderData(product, providerKey) {
        return product.virtualOptions?.providerMap?.[providerKey] || null;
    }

    disableConfirmButton() {
        const btn = document.getElementById('confirm-purchase-btn');
        if (btn) {
            btn.disabled = true;
        }
    }

    resetConfirmButton() {
        const btn = document.getElementById('confirm-purchase-btn');
        if (btn) {
            btn.disabled = false;
            btn.textContent = i18n?.t('products.modalConfirm') || '确认购买';
        }
    }

    handleApiKeyError(error, renderNotice = false) {
        if (error?.code !== 'API_KEY_REQUIRED') {
            return false;
        }
        const message = i18n?.t('common.apiKeyRequired') || '请先创建 API Key 才能执行该操作';
        this.showToast(message, 'warning');
        if (renderNotice) {
            this.renderApiKeyNotice(message);
        }
        return true;
    }

    renderApiKeyNotice(message) {
        ['static', 'dynamic', 'mobile'].forEach((category) => {
            const container = document.getElementById(`${category}-products`);
            if (container) {
                container.innerHTML = `
                    <div class="col-12 text-center text-muted">
                        <i class="fas fa-key fa-2x mb-2"></i>
                        <div>${message}</div>
                    </div>
                `;
            }
        });
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
