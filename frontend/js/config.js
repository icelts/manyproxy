(function () {
    function resolveStorage(preferred, fallback) {
        try {
            if (preferred) {
                const testKey = "__storage_test__";
                preferred.setItem(testKey, "1");
                preferred.removeItem(testKey);
                return preferred;
            }
        } catch (_) {
            // ignore
        }
        return fallback || null;
    }

    class SecureStorage {
        constructor(options = {}) {
            const local = options.localStorage ?? window.localStorage;
            const session = options.sessionStorage ?? window.sessionStorage;
            this.primary = resolveStorage(local, session);
            this.backup =
                this.primary === local && session ? session : null;
            this.keysToSync = options.keysToSync || [];
            this.syncFromBackup();
        }

        syncFromBackup() {
            if (!this.primary || !this.backup) return;
            this.keysToSync.forEach((key) => {
                try {
                    const backupValue = this.backup.getItem(key);
                    if (
                        backupValue !== null &&
                        this.primary.getItem(key) === null
                    ) {
                        this.primary.setItem(key, backupValue);
                    }
                } catch (error) {
                    console.warn(`Failed to sync key ${key}`, error);
                }
            });
        }

        getItem(key) {
            try {
                return this.primary?.getItem(key) ?? null;
            } catch (error) {
                console.warn(`SecureStorage.getItem(${key}) failed`, error);
                return null;
            }
        }

        setItem(key, value) {
            try {
                this.primary?.setItem(key, value);
                if (this.backup) {
                    this.backup.setItem(key, value);
                }
            } catch (error) {
                console.warn(`SecureStorage.setItem(${key}) failed`, error);
            }
        }

        removeItem(key) {
            try {
                this.primary?.removeItem(key);
                if (this.backup) {
                    this.backup.removeItem(key);
                }
            } catch (error) {
                console.warn(`SecureStorage.removeItem(${key}) failed`, error);
            }
        }
    }

    const storageKeys = [
        "access_token",
        "api_key",
        "user_info",
        "username",
        "is_admin",
        "api_calls",
        "session_envelope",
    ];

    const secureStorage = new SecureStorage({ keysToSync: storageKeys });
    window.secureStorage = secureStorage;

    class Config {
        constructor() {
            this.api = {
                baseURL: "http://localhost:8000/api/v1",
                timeout: 30000,
                retryCount: 3,
            };

            this.app = {
                name: "ManyProxy",
                version: "1.0.0",
                debug: true,
            };

            this.storage = {
                tokenKey: "access_token",
                apiKeyKey: "api_key",
                userKey: "user_info",
            };

            this.routes = {
                login: "/frontend/pages/login.html",
                dashboard: "/frontend/pages/dashboard.html",
                proxy: "/frontend/pages/proxy.html",
                apiKeys: "/frontend/pages/api-keys.html",
                admin: "/frontend/pages/admin.html",
            };
        }

        getBaseURL() {
            return this.api.baseURL;
        }

        setBaseURL(url) {
            this.api.baseURL = url;
        }

        getStorageKey(key) {
            return this.storage[key] || key;
        }

        getRoute(route) {
            return this.routes[route] || route;
        }
    }

    window.config = new Config();
})();
