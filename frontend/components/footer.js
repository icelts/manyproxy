(function () {
    const loadFooter = () => {
        const container = document.getElementById('footer-container');
        if (!container) return;
        
        // 服务器部署时统一通过绝对路径加载，文件协议下再退回旧逻辑
        const pathname = window.location.pathname;
        const isFileProtocol = window.location.protocol === 'file:';
        let footerPath = '/components/footer.html';

        if (isFileProtocol) {
            footerPath = pathname.includes('/pages/')
                ? '../components/footer.html'
                : 'components/footer.html';
        }
        
        fetch(footerPath)
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.text();
            })
            .then((html) => {
                container.innerHTML = html;
                if (window.i18n) {
                    i18n.applyStoredLanguage(container);
                }
            })
            .catch((error) => {
                console.error('加载页脚失败:', error);
                console.error('尝试加载的路径:', footerPath);
                console.error('当前页面路径:', pathname);
            });
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadFooter);
    } else {
        loadFooter();
    }
})();
