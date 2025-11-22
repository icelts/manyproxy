// 修复模态框问题的脚本
console.log('🔧 开始修复模态框问题...');

// 等待页面和AdminPage加载完成
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 页面加载完成，等待AdminPage初始化...');
    
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
        
        // 修复模态框CSS问题
        const modalStyles = `
            <style id="modal-fix-styles">
                .modal {
                    display: none !important;
                    position: fixed !important;
                    z-index: 10000 !important;
                    left: 0 !important;
                    top: 0 !important;
                    width: 100% !important;
                    height: 100% !important;
                    background-color: rgba(0,0,0,0.5) !important;
                }
                
                .modal.show {
                    display: block !important;
                }
                
                .modal-content {
                    background-color: #fefefe !important;
                    margin: 5% auto !important;
                    padding: 20px !important;
                    border: 1px solid #888 !important;
                    width: 80% !important;
                    max-width: 800px !important;
                    max-height: 80vh !important;
                    overflow-y: auto !important;
                    border-radius: 8px !important;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
                }
                
                .modal-header {
                    display: flex !important;
                    justify-content: space-between !important;
                    align-items: center !important;
                    margin-bottom: 20px !important;
                    padding-bottom: 10px !important;
                    border-bottom: 1px solid #eee !important;
                }
                
                .modal-header h4 {
                    margin: 0 !important;
                    color: #333 !important;
                }
                
                .close {
                    color: #aaa !important;
                    font-size: 28px !important;
                    font-weight: bold !important;
                    cursor: pointer !important;
                    background: none !important;
                    border: none !important;
                }
                
                .close:hover {
                    color: #000 !important;
                }
                
                .form-group {
                    margin-bottom: 15px !important;
                }
                
                .form-group label {
                    display: block !important;
                    margin-bottom: 5px !important;
                    font-weight: bold !important;
                    color: #333 !important;
                }
                
                .form-control {
                    width: 100% !important;
                    padding: 8px 12px !important;
                    border: 1px solid #ddd !important;
                    border-radius: 4px !important;
                    font-size: 14px !important;
                    box-sizing: border-box !important;
                }
                
                .modal-actions {
                    text-align: right !important;
                    margin-top: 20px !important;
                    padding-top: 15px !important;
                    border-top: 1px solid #eee !important;
                }
                
                .btn {
                    padding: 8px 16px !important;
                    margin-left: 10px !important;
                    border: none !important;
                    border-radius: 4px !important;
                    cursor: pointer !important;
                    font-size: 14px !important;
                }
                
                .btn-primary {
                    background-color: #007bff !important;
                    color: white !important;
                }
                
                .btn-outline {
                    background-color: #f8f9fa !important;
                    color: #6c757d !important;
                    border: 1px solid #6c757d !important;
                }
                
                .row {
                    display: flex !important;
                    margin: 0 -10px !important;
                }
                
                .col-md-6 {
                    flex: 0 0 50% !important;
                    padding: 0 10px !important;
                }
                
                .col-md-4 {
                    flex: 0 0 33.333% !important;
                    padding: 0 10px !important;
                }
                
                .text-danger {
                    color: #dc3545 !important;
                }
            </style>
        `;
        
        // 添加修复样式到页面
        if (!document.getElementById('modal-fix-styles')) {
            document.head.insertAdjacentHTML('beforeend', modalStyles);
            console.log('✅ 模态框修复样式已添加');
        }
        
        // 重写editProduct方法以确保模态框显示
        const originalEditProduct = window.adminPage.editProduct;
        window.adminPage.editProduct = function(productId) {
            console.log('🔧 修复版 editProduct 被调用，productId:', productId);
            
            try {
                // 调用原始方法
                const result = originalEditProduct.call(this, productId);
                
                // 强制显示模态框
                setTimeout(() => {
                    const modal = document.getElementById('productModal');
                    if (modal) {
                        console.log('🎯 强制显示模态框');
                        modal.style.display = 'block';
                        modal.classList.add('show');
                        
                        // 确保模态框在最顶层
                        modal.style.zIndex = '10000';
                        
                        // 添加调试信息
                        console.log('模态框状态:', {
                            display: modal.style.display,
                            classList: modal.className,
                            zIndex: modal.style.zIndex
                        });
                    } else {
                        console.error('❌ 找不到 productModal 元素');
                    }
                }, 100);
                
                return result;
            } catch (error) {
                console.error('❌ editProduct 执行出错:', error);
                
                // 手动显示模态框
                const modal = document.getElementById('productModal');
                if (modal) {
                    modal.style.display = 'block';
                    modal.classList.add('show');
                }
            }
        };
        
        console.log('✅ editProduct 方法已修复');
        
        // 添加全局测试函数
        window.testEditProduct = function() {
            console.log('🧪 测试编辑产品功能');
            if (window.adminPage && window.adminPage.editProduct) {
                window.adminPage.editProduct(13);
            } else {
                console.error('❌ adminPage.editProduct 不可用');
            }
        };
        
        // 添加修复信息到页面
        const fixInfo = document.createElement('div');
        fixInfo.id = 'fix-info';
        fixInfo.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: #28a745;
            color: white;
            padding: 10px;
            border-radius: 5px;
            z-index: 9999;
            font-size: 12px;
            max-width: 300px;
        `;
        fixInfo.innerHTML = `
            <h6>✅ 模态框已修复</h6>
            <p>AdminPage: ✅</p>
            <p>editProduct: ✅</p>
            <p>样式: ✅</p>
            <button onclick="testEditProduct()" style="background: white; color: #28a745; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">测试编辑</button>
        `;
        document.body.appendChild(fixInfo);
        
        // 5秒后自动隐藏修复信息
        setTimeout(() => {
            if (fixInfo.parentNode) {
                fixInfo.parentNode.removeChild(fixInfo);
            }
        }, 5000);
        
        console.log('🎉 模态框修复完成！');
        
    }, 2000); // 等待2秒确保所有脚本加载完成
});

console.log('🎯 修复脚本已加载');
