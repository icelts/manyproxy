// 国际化支持
const i18n = {
    currentLang: localStorage.getItem('language') || 'zh',
    
    translations: {
        zh: {
            // 导航栏
            'nav.home': '首页',
            'nav.products': '产品',
            'nav.pricing': '价格',
            'nav.dashboard': '仪表板',
            'nav.proxy': '代理管理',
            'nav.api_keys': 'API密钥',
            'nav.login': '登录',
            'nav.register': '注册',
            'nav.logout': '退出登录',
            'nav.language': '语言',
            
            // 首页
            'home.title': 'ManyProxy - 专业代理服务平台',
            'home.subtitle': '提供静态代理、动态代理、移动代理等多种代理服务',
            'home.features.title': '我们的优势',
            'home.features.stability.title': '高稳定性',
            'home.features.stability.desc': '99.9%在线保证，24/7技术支持',
            'home.features.speed.title': '高速连接',
            'home.features.speed.desc': '全球节点，低延迟高速访问',
            'home.features.security.title': '安全可靠',
            'home.features.security.desc': '加密传输，保护您的隐私安全',
            'home.features.easy.title': '简单易用',
            'home.features.easy.desc': '一键配置，支持多种协议',
            
            // 产品介绍
            'products.static.title': '静态代理',
            'products.static.desc': '固定IP地址，适合长期稳定使用',
            'products.dynamic.title': '动态代理',
            'products.dynamic.desc': '自动轮换IP，适合爬虫和数据采集',
            'products.mobile.title': '移动代理',
            'products.mobile.desc': '真实移动网络IP，支持4G/5G网络',
            
            // 价格
            'pricing.title': '价格方案',
            'pricing.basic': '基础版',
            'pricing.professional': '专业版',
            'pricing.enterprise': '企业版',
            'pricing.contact': '联系销售',
            
            // 底部
            'footer.copyright': '© 2024 ManyProxy. 保留所有权利。',
            'footer.contact': '联系我们',
            'footer.api_docs': 'API文档',
            'footer.privacy': '隐私政策',
            'footer.terms': '服务条款',
            'footer.about': '关于我们',
            'footer.support': '技术支持',
            
            // 通用
            'btn.get_started': '开始使用',
            'btn.learn_more': '了解更多',
            'btn.buy_now': '立即购买',
            'price.from': '起',
            'price.month': '/月'
        },
        
        en: {
            // Navigation
            'nav.home': 'Home',
            'nav.products': 'Products',
            'nav.pricing': 'Pricing',
            'nav.dashboard': 'Dashboard',
            'nav.proxy': 'Proxy Management',
            'nav.api_keys': 'API Keys',
            'nav.login': 'Login',
            'nav.register': 'Register',
            'nav.logout': 'Logout',
            'nav.language': 'Language',
            
            // Home
            'home.title': 'ManyProxy - Professional Proxy Service Platform',
            'home.subtitle': 'Providing static proxies, dynamic proxies, mobile proxies and more',
            'home.features.title': 'Our Advantages',
            'home.features.stability.title': 'High Stability',
            'home.features.stability.desc': '99.9% uptime guarantee, 24/7 technical support',
            'home.features.speed.title': 'High Speed',
            'home.features.speed.desc': 'Global nodes, low latency high-speed access',
            'home.features.security.title': 'Secure & Reliable',
            'home.features.security.desc': 'Encrypted transmission, protect your privacy',
            'home.features.easy.title': 'Easy to Use',
            'home.features.easy.desc': 'One-click configuration, support multiple protocols',
            
            // Products
            'products.static.title': 'Static Proxies',
            'products.static.desc': 'Fixed IP address, suitable for long-term stable use',
            'products.dynamic.title': 'Dynamic Proxies',
            'products.dynamic.desc': 'Automatic IP rotation, suitable for crawling and data collection',
            'products.mobile.title': 'Mobile Proxies',
            'products.mobile.desc': 'Real mobile network IPs, support 4G/5G networks',
            
            // Pricing
            'pricing.title': 'Pricing Plans',
            'pricing.basic': 'Basic',
            'pricing.professional': 'Professional',
            'pricing.enterprise': 'Enterprise',
            'pricing.contact': 'Contact Sales',
            
            // Footer
            'footer.copyright': '© 2024 ManyProxy. All rights reserved.',
            'footer.contact': 'Contact Us',
            'footer.api_docs': 'API Documentation',
            'footer.privacy': 'Privacy Policy',
            'footer.terms': 'Terms of Service',
            'footer.about': 'About Us',
            'footer.support': 'Technical Support',
            
            // Common
            'btn.get_started': 'Get Started',
            'btn.learn_more': 'Learn More',
            'btn.buy_now': 'Buy Now',
            'price.from': 'From',
            'price.month': '/month'
        }
    },
    
    t(key) {
        const keys = key.split('.');
        let value = this.translations[this.currentLang];
        
        for (const k of keys) {
            value = value?.[k];
        }
        
        return value || key;
    },
    
    setLang(lang) {
        this.currentLang = lang;
        localStorage.setItem('language', lang);
        this.updatePage();
    },
    
    updatePage() {
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            element.textContent = this.t(key);
        });
        
        // Update HTML lang attribute
        document.documentElement.lang = this.currentLang;
        
        // Update language switcher
        document.querySelectorAll('.lang-switcher').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === this.currentLang);
        });
    }
};

// Initialize i18n when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    i18n.updatePage();
});
