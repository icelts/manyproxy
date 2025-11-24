// API配置和调用模块
const storage = window.secureStorage || window.sessionStorage;

class API {
    constructor() {
        this.baseURL = config.getBaseURL();
        this.token = storage.getItem(config.getStorageKey('tokenKey'));
        this.apiKey = storage.getItem(config.getStorageKey('apiKeyKey'));
    }

    // 设置认证令牌
    setToken(token) {
        this.token = token;
        storage.setItem(config.getStorageKey('tokenKey'), token);
    }

    // 设置API密钥
    setApiKey(apiKey) {
        this.apiKey = apiKey;
        storage.setItem(config.getStorageKey('apiKeyKey'), apiKey);
    }

    // 清除认证信息
    clearAuth() {
        this.token = null;
        this.apiKey = null;
        storage.removeItem(config.getStorageKey('tokenKey'));
        storage.removeItem(config.getStorageKey('apiKeyKey'));
        storage.removeItem(config.getStorageKey('userKey'));
    }

    // 通用请求方法
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const requestConfig = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        // 添加认证头
        if (this.token) {
            requestConfig.headers.Authorization = `Bearer ${this.token}`;
        } else if (this.apiKey) {
            requestConfig.headers['X-API-Key'] = this.apiKey;
        }

        try {
            const response = await fetch(url, requestConfig);
            const data = await response.json();

            if (!response.ok) {
                const apiError = new Error(data.detail || `HTTP error! status: ${response.status}`);
                apiError.status = response.status;
                apiError.response = data;
                
                // 如果是401错误，清除本地认证信息
                if (response.status === 401) {
                    console.log('收到401错误，准备刷新会话');
                    if (window.sessionController) {
                        await window.sessionController.safeRefresh();
                    }
                }
                
                throw apiError;
            }

            return data;
        } catch (error) {
            console.error('API请求失败:', error);
            
            // 如果是网络错误且不是401，保持认证状态
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                console.log('网络错误，保持认证状态');
            }
            
            throw error;
        }
    }

    // GET请求
    async get(endpoint, options = {}) {
        let url = endpoint;
        const requestOptions = { method: 'GET', ...options };
        
        // 处理查询参数
        if (options.params) {
            const searchParams = new URLSearchParams();
            Object.keys(options.params).forEach(key => {
                if (options.params[key] !== undefined && options.params[key] !== null) {
                    searchParams.append(key, options.params[key]);
                }
            });
            const queryString = searchParams.toString();
            if (queryString) {
                url += (url.includes('?') ? '&' : '?') + queryString;
            }
            // 从requestOptions中移除params，避免传递给fetch
            delete requestOptions.params;
        }
        
        return this.request(url, requestOptions);
    }

    // POST请求
    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // PUT请求
    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    // DELETE请求
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // 认证相关API
    async login(username, password) {
        const data = await this.post('/session/login', { username, password });
        this.setToken(data.token);
        return data;
    }

    async register(userData) {
        const data = await this.post('/session/register', userData);
        this.setToken(data.token);
        return data;
    }

    async createApiKey(name, rateLimit) {
        return this.post('/session/api-keys', { name, rate_limit: rateLimit });
    }

    async getApiKeys() {
        return this.get('/session/api-keys');
    }

    async rotateApiKey(keyId) {
        return this.put(`/session/api-keys/${keyId}`);
    }

    async deleteApiKey(keyId) {
        return this.delete(`/session/api-keys/${keyId}`);
    }

    // 代理相关API
    async getProxyProducts() {
        return this.get('/proxy/products');
    }

    async buyStaticProxy(provider, quantity) {
        return this.post('/proxy/static/buy', { provider, quantity });
    }

    async buyDynamicProxy(packageType, quantity) {
        return this.post('/proxy/dynamic/buy', { 
            package_type: packageType, 
            quantity 
        });
    }

    async buyMobileProxy(provider, quantity) {
        return this.post('/proxy/mobile/buy', { provider, quantity });
    }

    async getProxyList() {
        return this.get('/proxy/list');
    }

    async getDynamicProxy(orderId) {
        return this.get(`/proxy/dynamic/${orderId}`);
    }

    async getDynamicProxyByToken(token, carrier = 'random', province = '0') {
        const params = new URLSearchParams({ carrier, province });
        return this.get(`/proxy/dynamic/token/${token}?${params.toString()}`);
    }

    async resetMobileProxy(orderId) {
        return this.post(`/proxy/mobile/${orderId}/reset`);
    }

    async resetMobileProxyByToken(token) {
        return this.post(`/proxy/mobile/token/${token}/reset`);
    }

    async getProxyStats() {
        return this.get('/proxy/stats');
    }

    // 新增静态代理管理API
    async getSupportedProviders() {
        return this.get('/proxy/static/providers');
    }

    async changeStaticProxy(orderId, targetProvider, protocol = 'HTTP', username = 'random', password = 'random') {
        const params = new URLSearchParams({
            target_provider: targetProvider,
            protocol: protocol,
            username: username,
            password: password
        });
        return this.post(`/proxy/static/${orderId}/change?${params}`);
    }

    async changeProxySecurity(orderId, protocol = 'HTTP', username = 'random', password = 'random') {
        const params = new URLSearchParams({
            protocol: protocol,
            username: username,
            password: password
        });
        return this.post(`/proxy/static/${orderId}/change-security?${params}`);
    }

    async renewStaticProxy(orderId, days) {
        const params = new URLSearchParams({ days: days.toString() });
        return this.post(`/proxy/static/${orderId}/renew?${params}`);
    }

    async getUpstreamProxyList(provider, proxyId = null) {
        const params = new URLSearchParams({ provider: provider });
        if (proxyId) params.append('proxy_id', proxyId);
        return this.get(`/proxy/static/upstream-list?${params}`);
    }

    // 获取用户信息
    async getSessionState() {
        return this.get('/session/state');
    }

    async getUserInfo() {
        const state = await this.getSessionState();
        return state.user;
    }

    // 健康检查
    async healthCheck() {
        return this.get('/health');
    }
}

// 创建全局API实例
const api = new API();

// 导出API实例
window.api = api;
