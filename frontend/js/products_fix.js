// 修复购买成功后无提示和跳转的问题

// 在ProductsPage类的confirmPurchase方法中，静态代理购买成功后没有调用handlePurchaseSuccess
// 问题在于静态代理购买逻辑中，await this.submitStaticPurchase()之后直接return了，没有执行后续的handlePurchaseSuccess

// 修复后的confirmPurchase方法
async confirmPurchase(product, quantity, modal) {
    try {
        if (product.category === 'static') {
            if (this.purchaseCompleted) {
                return;
            }
            // 修复：移除return，让代码继续执行到handlePurchaseSuccess
            await this.submitStaticPurchase(product, quantity, null, { modal });
            this.purchaseCompleted = true;
            this.disableConfirmButton();
            // 修复：调用购买成功处理
            await this.handlePurchaseSuccess(modal);
        } else if (product.category === 'dynamic') {
            await api.post('/proxy/dynamic/buy', {
                product_id: product.id,
                quantity
            });
            await this.handlePurchaseSuccess(modal);
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
            await this.handlePurchaseSuccess(modal);
        }
    } catch (error) {
        if (this.handleApiKeyError(error)) {
            modal.hide();
            return;
        }
        console.error('购买产品失败:', error);
        const message = error.response?.detail || error.message || i18n?.t('products.toast.createFailed') || '购买失败，请稍后重试';
        this.showToast(message, 'error');
    }
}

// 修复submitStaticPurchase方法，移除重复的handlePurchaseSuccess调用
async submitStaticPurchase(product, quantity, inlineValues = null, options = {}) {
    const formValues = inlineValues || this.readStaticFormValues();

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
    // 修复：移除这里的handlePurchaseSuccess调用，让confirmPurchase统一处理
    // await this.handlePurchaseSuccess(options.modal || null);
    return order;
}

console.log('购买成功处理修复已加载');
