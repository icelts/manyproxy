// 调试模态框问题的脚本
console.log('🔧 开始调试模态框问题...');

// 等待页面加载完成
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 页面加载完成，开始调试...');
    
    // 等待AdminPage初始化
    setTimeout(function() {
        console.log('🔍 检查AdminPage状态...');
        
        if (typeof window.adminPage === 'undefined') {
            console.error('❌ adminPage 未定义');
            return;
        }
        
        if (typeof window.adminPage.editProduct === 'undefined') {
            console.error('❌ editProduct 方法未定义');
            return;
        }
        
        console.log('✅ AdminPage 和 editProduct 方法都存在');
        
        // 添加调试信息到页面
        const debugInfo = document.createElement('div');
        debugInfo.id = 'debug-info';
        debugInfo.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: #fff;
            border: 2px solid #007bff;
            padding: 10px;
            border-radius: 5px;
            z-index: 9999;
            font-size: 12px;
            max-width: 300px;
        `;
        debugInfo.innerHTML = `
            <h6>调试信息</h6>
            <p>AdminPage: ✅</p>
            <p>editProduct: ✅</p>
            <p>点击编辑按钮测试</p>
            <button onclick="testEditProduct()" style="background: #007bff; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">测试编辑</button>
        `;
        document.body.appendChild(debugInfo);
        
    }, 2000); // 等待2秒确保所有脚本加载完成
});

// 添加全局测试函数
window.testEditProduct = function() {
    console.log('🧪 测试编辑产品功能');
    if (window.adminPage && window.adminPage.editProduct) {
        window.adminPage.editProduct(13);
    } else {
        console.error('❌ adminPage.editProduct 不可用');
    }
};

console.log('🎯 调试脚本已加载');
