(function enforceSessionStorage() {
    try {
        const session = window.sessionStorage;
        const local = window.localStorage;
        if (!session || !local) {
            return;
        }
        const keys = [];
        for (let i = 0; i < local.length; i += 1) {
            const key = local.key(i);
            if (key) {
                keys.push(key);
            }
        }
        keys.forEach((key) => {
            const value = local.getItem(key);
            if (value !== null && session.getItem(key) === null) {
                session.setItem(key, value);
            }
        });
        local.clear();
        ['setItem', 'getItem', 'removeItem', 'clear', 'key'].forEach((method) => {
            if (typeof session[method] === 'function') {
                local[method] = session[method].bind(session);
            }
        });
    } catch (error) {
        console.warn('Failed to harden storage', error);
    }
})();

class SecureStorage {
    constructor(storage = window.sessionStorage) {
        this.storage = storage;
    }

    migrate(keys = []) {
        const legacy = window.localStorage;
        if (!legacy) return;
        keys.forEach((key) => {
            try {
                const legacyValue = legacy.getItem(key);
                if (legacyValue && !this.storage.getItem(key)) {
                    this.storage.setItem(key, legacyValue);
                }
                legacy.removeItem(key);
            } catch (error) {
                console.warn(`Failed to migrate key ${key}`, error);
            }
        });
    }

    getItem(key) {
        return this.storage.getItem(key);
    }

    setItem(key, value) {
        this.storage.setItem(key, value);
    }

    removeItem(key) {
        this.storage.removeItem(key);
    }
}

const secureStorage = new SecureStorage();
window.secureStorage = secureStorage;

// 全局配置中心
class Config {
    constructor() {
        // API配置
        this.api = {
            baseURL: 'http://localhost:8000/api/v1',
            timeout: 30000,
            retryCount: 3
        };

        // 应用配置
        this.app = {
            name: 'ManyProxy',
            version: '1.0.0',
            debug: true
        };

        // 存储配置
        this.storage = {
            tokenKey: 'access_token',
            apiKeyKey: 'api_key',
            userKey: 'user_info'
        };

        const keysToMigrate = [
            ...Object.values(this.storage),
            'username',
            'is_admin',
            'api_calls'
        ];
        secureStorage.migrate(keysToMigrate);

        // 路由配置
        this.routes = {
            login: '/frontend/pages/login.html',
            dashboard: '/frontend/pages/dashboard.html',
            proxy: '/frontend/pages/proxy.html',
            apiKeys: '/frontend/pages/api-keys.html',
            admin: '/frontend/pages/admin.html'
        };
    }

    // 获取API基础URL
    getBaseURL() {
        return this.api.baseURL;
    }

    // 设置API基础URL（用于动态配置）
    setBaseURL(url) {
        this.api.baseURL = url;
    }

    // 获取存储键名
    getStorageKey(key) {
        return this.storage[key] || key;
    }

    // 获取路由路径
    getRoute(route) {
        return this.routes[route] || route;
    }
}

// 创建全局配置实例
const config = new Config();

// 导出配置实例
window.config = config;
