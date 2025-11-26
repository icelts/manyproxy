// 导航栏通用逻辑
class NavbarManager {
    constructor() {
        this.init();
    }

    async init() {
        await sessionController.initialized;

        if (!sessionController.isAuthenticated()) {
            await sessionController.safeRefresh();
        }

        if (!sessionController.isAuthenticated()) {
            if (!window.location.pathname.includes('login.html') &&
                !window.location.pathname.includes('register.html')) {
                window.location.href = 'login.html';
            }
            return;
        }

        this.applyTranslations();
        this.renderUserInfo();
        sessionController.subscribe(() => this.renderUserInfo());

        this.bindLogoutEvent();
        this.setActiveNavigation();
    }

    renderUserInfo() {
        const user = sessionController.getUser();
        const usernameEl = document.getElementById('username');
        if (usernameEl && user?.username) {
            usernameEl.textContent = user.username;
        }

        const adminNavItem = document.getElementById('admin-nav-item');
        if (adminNavItem) {
            adminNavItem.style.display = sessionController.isAdmin() ? 'block' : 'none';
        }
    }

    bindLogoutEvent() {
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.removeEventListener('click', this.logoutHandler);
            this.logoutHandler = (e) => {
                e.preventDefault();
                this.logout();
            };
            logoutBtn.addEventListener('click', this.logoutHandler);
        }
    }

    // 重新绑定所有事件（用于动态加载后）
    rebindEvents() {
        this.bindLogoutEvent();
    }

    logout() {
        sessionController.logout({ redirectTo: 'login.html' });
    }

    setActiveNavigation() {
        // 获取当前页面路径
        const currentPath = window.location.pathname;
        const currentPage = currentPath.split('/').pop() || 'dashboard.html';
        
        // 查找对应的导航链接并设置为激活状态
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === currentPage) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }

    // 更新用户余额显示（如果页面有余额显示元素）
    async updateBalance() {
        try {
            const userInfo = await api.getUserInfo();
            const balanceElement = document.getElementById('user-balance');
            if (balanceElement) {
                balanceElement.textContent = userInfo.balance.toFixed(2);
            }
        } catch (error) {
            console.error('获取余额失败:', error);
        }
    }

    applyTranslations() {
        if (window.i18n) {
            const container = document.getElementById('navbar-container');
            if (container) {
                i18n.updatePage(container);
            } else {
                i18n.updatePage();
            }
            this.updateAuthLabels();
        }
    }

    updateAuthLabels() {
        if (!window.i18n) return;
        const loginText = i18n.currentLang === 'zh' ? '登录' : 'Login';
        const registerText = i18n.currentLang === 'zh' ? '注册' : 'Register';
        const loginLink = document.querySelector('[data-i18n=\"nav.login\"]');
        const registerLink = document.querySelector('[data-i18n=\"nav.register\"]');
        if (loginLink) loginLink.textContent = loginText;
        if (registerLink) registerLink.textContent = registerText;
    }
}

// 页面加载完成后初始化导航栏
document.addEventListener('DOMContentLoaded', function() {
    // 确保config和api已加载
    if (typeof config !== 'undefined' && typeof api !== 'undefined') {
        window.navbarManager = new NavbarManager();
    } else {
        // 如果config或api未加载，等待一段时间后再试
        setTimeout(() => {
            if (typeof config !== 'undefined' && typeof api !== 'undefined') {
                window.navbarManager = new NavbarManager();
            }
        }, 100);
    }
});
