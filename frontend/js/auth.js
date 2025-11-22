const sessionStorageEngine = window.secureStorage || window.sessionStorage;

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
        try {
            await this.refresh();
        } catch (error) {
            console.warn('Session refresh failed', error);
            this.clearState();
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
        if (!envelope || !envelope.token) {
            throw new Error('Invalid session envelope');
        }

        this.state = envelope;
        this.storage.setItem(this.sessionKey, JSON.stringify(envelope));
        this.storage.setItem(this.tokenKey, envelope.token);
        this.storage.setItem('username', envelope.user?.username || '');
        this.storage.setItem(this.userKey, JSON.stringify(envelope.user || {}));

        api.setToken(envelope.token);
        this.emitChange();
    }

    clearState() {
        this.state = null;
        this.storage.removeItem(this.sessionKey);
        this.storage.removeItem('username');
        api.clearAuth();
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
        const envelope = await api.getSessionState();
        this.setState(envelope);
        return envelope;
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
