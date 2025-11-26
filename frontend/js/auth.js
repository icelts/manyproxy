const sessionStorageEngine = window.secureStorage || window.localStorage || window.sessionStorage;

class SessionController {
    constructor(storage = sessionStorageEngine) {
        this.storage = storage;
        this.tokenKey = config.getStorageKey('tokenKey');
        this.userKey = config.getStorageKey('userKey');
        this.sessionKey = 'session_envelope';
        this.state = null;
        this.listeners = new Set();
        this.initialized = this.bootstrap();
    }

    async bootstrap() {
        const cached = this.storage.getItem(this.sessionKey);
        if (cached) {
            try {
                this.state = JSON.parse(cached);
                if (this.state?.token) {
                    api.setToken(this.state.token);
                }
                if (this.state?.api_key) {
                    api.setApiKey(this.state.api_key);
                }
            } catch (error) {
                console.warn('Failed to parse cached session', error);
                this.storage.removeItem(this.sessionKey);
            }
        }

        const token = this.storage.getItem(this.tokenKey);
        if (token && !this.state) {
            await this.safeRefresh();
        } else if (!token && !this.state) {
            this.clearState();
        }
    }

    async safeRefresh() {
        if (this.isRefreshing) {
            console.log('Already refreshing, skipping...');
            return;
        }
        
        this.isRefreshing = true;
        try {
            await this.refresh();
        } catch (error) {
            console.warn('Session refresh failed', error);
            // 如果是500错误，不要清除状态，保持现有登录状态
            if (error.message && error.message.includes('500')) {
                console.log('Session state 500 error, keeping current session');
                return;
            }
            this.clearState();
        } finally {
            this.isRefreshing = false;
        }
    }

    subscribe(listener) {
        this.listeners.add(listener);
        if (this.state) {
            listener(this.state);
        }
        return () => this.listeners.delete(listener);
    }

    emitChange() {
        this.listeners.forEach((listener) => {
            try {
                listener(this.state);
            } catch (error) {
                console.warn('Session listener error', error);
            }
        });
    }

    setState(envelope) {
        // 支持API Key登录，此时可能没有token
        if (!envelope || (!envelope.token && !envelope.api_key)) {
            throw new Error('Invalid session envelope');
        }

        this.state = envelope;
        this.storage.setItem(this.sessionKey, JSON.stringify(envelope));
        
        if (envelope.token) {
            this.storage.setItem(this.tokenKey, envelope.token);
        }
        
        if (envelope.api_key) {
            api.setApiKey(envelope.api_key);
        }
        
        this.storage.setItem('username', envelope.user?.username || '');
        this.storage.setItem(this.userKey, JSON.stringify(envelope.user || {}));

        if (envelope.token) {
            api.setToken(envelope.token);
        }
        
        this.emitChange();
    }

    clearState() {
        this.state = null;
        this.storage.removeItem(this.sessionKey);
        this.storage.removeItem('username');
        api.clearAuth();
        this.emitChange();
    }

    updateApiKey(apiKey) {
        if (!this.state) {
            this.state = {
                api_key: null,
                user: null,
                abilities: {},
                pages: {},
            };
        }
        this.state.api_key = apiKey || null;
        this.storage.setItem(this.sessionKey, JSON.stringify(this.state));
        api.setApiKey(apiKey || null);
        this.emitChange();
    }

    getSession() {
        return this.state;
    }

    getUser() {
        return this.state?.user || null;
    }

    getPages() {
        return this.state?.pages || {};
    }

    getPageReason(pageName) {
        return this.getPages()[pageName]?.reason || null;
    }

    getAbilities() {
        return this.state?.abilities || {};
    }

    isAuthenticated() {
        return !!this.state?.user;
    }

    isAdmin() {
        return !!this.state?.user?.is_admin;
    }

    canAccess(pageName) {
        if (!pageName) {
            return this.isAuthenticated();
        }
        const pageState = this.getPages()[pageName];
        if (!pageState) {
            return this.isAuthenticated();
        }
        return pageState.allowed;
    }

    async login(username, password) {
        const envelope = await api.login(username, password);
        this.setState(envelope);
        return envelope;
    }

    async register(payload) {
        const envelope = await api.register(payload);
        this.setState(envelope);
        return envelope;
    }

    async refresh() {
        const token = this.storage.getItem(this.tokenKey);
        if (!token) {
            this.clearState();
            return null;
        }
        api.setToken(token);
        try {
            const envelope = await api.getSessionState();
            this.setState(envelope);
            return envelope;
        } catch (error) {
            console.warn('Session state refresh failed, but keeping token:', error);
            // 如果session state失败，但token存在，创建一个基本的session state
            const username = this.storage.getItem('username');
            if (username && token) {
                const basicEnvelope = {
                    token: token,
                    token_type: "bearer",
                    api_key: this.storage.getItem(config.getStorageKey('apiKeyKey')),
                    user: {
                        username: username,
                        is_active: true
                    },
                    abilities: {
                        can_purchase: true,
                        can_use_api: true,
                        can_manage_platform: false,
                        can_access_admin: false
                    },
                    pages: {
                        dashboard: { allowed: true, reason: null },
                        proxy: { allowed: true, reason: null },
                        products: { allowed: true, reason: null },
                        orders: { allowed: true, reason: null },
                        "api-keys": { allowed: true, reason: null },
                        profile: { allowed: true, reason: null },
                        admin: { allowed: false, reason: "ADMIN_ONLY" }
                    },
                    refreshed_at: new Date().toISOString()
                };
                this.setState(basicEnvelope);
                return basicEnvelope;
            } else {
                this.clearState();
                return null;
            }
        }
    }

    async logout(options = {}) {
        try {
            await api.post('/session/logout', {});
        } catch (error) {
            console.warn('Session logout failed', error);
        }
        this.clearState();
        if (options.redirectTo) {
            window.location.href = options.redirectTo;
        }
    }

    async ensurePage(pageName, { redirectTo, message } = {}) {
        await this.initialized;
        if (!this.isAuthenticated()) {
            await this.safeRefresh();
        }
        if (this.canAccess(pageName)) {
            return true;
        }

        const fallbackMessage =
            message ||
            (this.getPageReason(pageName) === 'ADMIN_ONLY'
                ? '当前账号没有管理员权限，即将返回登录页面。'
                : '登录状态已失效，请重新登录。');

        if (fallbackMessage) {
            alert(fallbackMessage);
        }
        if (redirectTo) {
            window.location.href = redirectTo;
        }
        throw new Error(`PAGE_ACCESS_DENIED:${pageName}`);
    }
}

const sessionController = new SessionController();

window.sessionController = sessionController;
window.authManager = sessionController;
window.auth = sessionController;
