class ProfilePage {
    async init() {
        await this.loadUserInfo();
        await this.loadApiKey();
        this.bindEvents();
    }

    async loadUserInfo() {
        try {
            const user = sessionController.getUser() || await api.getUserInfo();
            if (user?.is_admin) {
                const adminNavItem = document.getElementById('admin-nav-item');
                if (adminNavItem) adminNavItem.style.display = 'block';
            }
            this.renderUserInfo(user);
        } catch (error) {
            this.handleAuthError(error, i18n?.t('profile.toast.loadFailed') || '无法获取 API 密钥');
        }
    }

    renderUserInfo(user) {
        if (!user) return;
        document.getElementById('profile-username').textContent = user.username || '--';
        document.getElementById('profile-email').textContent = user.email || '--';
        document.getElementById('profile-balance').textContent = `$${Number(user.balance || 0).toFixed(2)}`;
        document.getElementById('profile-created').textContent = this.formatDate(user.created_at);
    }

    async loadApiKey() {
        try {
            const keys = await api.getApiKeys();
            const activeKey = (keys || []).find((key) => key.is_active) || keys?.[0];
            if (activeKey) {
                document.getElementById('api-key-display').value = activeKey.api_key;
                document.getElementById('reset-api-key').dataset.keyId = activeKey.id;
                sessionController.updateApiKey(activeKey.api_key);
            } else {
                const created = await this.createApiKey(i18n?.t('profile.apiPlaceholder') || '默认密钥');
                document.getElementById('api-key-display').value = created.api_key;
                document.getElementById('reset-api-key').dataset.keyId = created.id;
                sessionController.updateApiKey(created.api_key);
            }
        } catch (error) {
            this.handleAuthError(error, i18n?.t('profile.toast.loadFailed') || '无法获取 API 密钥');
        }
    }

    bindEvents() {
        document.getElementById('copy-api-key').addEventListener('click', () => this.copyApiKey());
        document.getElementById('reset-api-key').addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('resetApiKeyModal'));
            modal.show();
        });
        document.getElementById('confirm-reset-api-key').addEventListener('click', () => this.resetApiKey());
        document.getElementById('change-password-form').addEventListener('submit', (e) => this.changePassword(e));
    }

    copyApiKey() {
        const input = document.getElementById('api-key-display');
        const value = input.value || '';
        if (!value || value === i18n?.t('profile.apiPlaceholder')) return;

        navigator.clipboard.writeText(value)
            .then(() => this.showToast(i18n?.t('profile.toast.copySuccess') || 'API 密钥已复制', 'success'))
            .catch(() => this.showToast(i18n?.t('profile.toast.copyFailed') || '复制失败，请手动复制', 'error'));
    }

    async createApiKey(name = '默认密钥') {
        try {
            const result = await api.createApiKey(name, 1000);
            this.showToast(i18n?.t('profile.toast.createSuccess') || '已创建新的 API 密钥', 'success');
            sessionController.updateApiKey(result.api_key);
            return result;
        } catch (error) {
            this.handleAuthError(error, i18n?.t('profile.toast.loadFailed') || '创建 API 密钥失败');
            throw error;
        }
    }

    async resetApiKey() {
        const button = document.getElementById('confirm-reset-api-key');
        button.disabled = true;
        button.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${i18n?.t('common.loading') || '加载中...'}`;

        try {
            const keys = await api.getApiKeys();
            const active = (keys || []).find((key) => key.is_active) || keys?.[0];
            let result;
            if (active) {
                result = await api.rotateApiKey(active.id);
                document.getElementById('reset-api-key').dataset.keyId = active.id;
            } else {
                result = await this.createApiKey('默认密钥');
                document.getElementById('reset-api-key').dataset.keyId = result.id;
            }
            document.getElementById('api-key-display').value = result.api_key;
            sessionController.updateApiKey(result.api_key);
            this.showToast(i18n?.t('profile.toast.regenSuccess') || 'API 密钥已重新生成', 'success');
            bootstrap.Modal.getInstance(document.getElementById('resetApiKeyModal')).hide();
        } catch (error) {
            this.handleAuthError(error, error.message || i18n?.t('profile.toast.loadFailed') || '重新生成失败');
        } finally {
            button.disabled = false;
            button.textContent = i18n?.t('profile.modalConfirm') || '确认生成';
        }
    }

    async changePassword(event) {
        event.preventDefault();
        const currentPassword = document.getElementById('current-password').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        const submitBtn = event.target.querySelector('button[type="submit"]');

        if (newPassword !== confirmPassword) {
            this.showToast(i18n?.t('profile.toast.passwordMismatch') || '两次输入的密码不一致', 'error');
            return;
        }
        if (newPassword.length < 6) {
            this.showToast(i18n?.t('profile.toast.passwordShort') || '密码长度至少 6 位', 'error');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${i18n?.t('common.buttons.save') || '保存'}`;

        try {
            const response = await fetch('/api/v1/session/change-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${sessionController.getSession()?.token || ''}`,
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword,
                }),
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || '修改失败');
            }

            this.showToast(i18n?.t('profile.toast.passwordSaved') || '密码修改成功', 'success');
            event.target.reset();
        } catch (error) {
            this.handleAuthError(error, error.message || i18n?.t('profile.toast.loadFailed') || '修改失败');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = i18n?.t('profile.savePassword') || '保存密码';
        }
    }

    handleAuthError(error, fallback = '操作失败') {
        console.error(error);
        if (error?.status === 401 || error?.status === 403) {
            this.showToast(i18n?.t('profile.toast.loginExpired') || '登录已失效，请重新登录', 'error');
            setTimeout(() => sessionController.logout({ redirectTo: 'login.html' }), 1500);
        } else {
            this.showToast(fallback, 'error');
        }
    }

    formatDate(value) {
        if (!value) return '--';
        const locale = i18n?.currentLang === 'en' ? 'en-US' : 'zh-CN';
        return new Date(value).toLocaleString(locale, { hour12: false });
    }

    showToast(message, type = 'info') {
        const toastEl = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');
        if (!toastEl || !toastMessage) return;

        toastEl.className = 'toast';
        toastEl.classList.add(
            type === 'success' ? 'bg-success text-white' :
            type === 'error' ? 'bg-danger text-white' :
            'bg-info text-white'
        );
        toastMessage.textContent = message;
        new bootstrap.Toast(toastEl).show();
    }
}

const profilePage = new ProfilePage();
window.profilePage = profilePage;
