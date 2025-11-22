(function () {
    const loadFooter = () => {
        const container = document.getElementById('footer-container');
        if (!container) return;
        const isPage = window.location.pathname.includes('/frontend/pages/');
        const footerPath = isPage ? '../components/footer.html' : 'components/footer.html';
        fetch(footerPath)
            .then((response) => response.text())
            .then((html) => {
                container.innerHTML = html;
            })
            .catch((error) => console.error('加载页脚失败:', error));
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadFooter);
    } else {
        loadFooter();
    }
})();
