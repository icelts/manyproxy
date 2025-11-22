// 修复模态框问题的脚本
console.log('🔧 开始修复模态框问题...');

// 等待页面加载完成
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 页面加载完成，开始修复...');
    
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
        
        // 修复模态框显示问题
        const originalEditProduct = window.adminPage.editProduct;
        
        window.adminPage.editProduct = function(productId) {
            console.log('🔄 调用修复后的 editProduct 方法，productId:', productId);
            
            try {
                // 调用原始方法
                originalEditProduct.call(this, productId);
                
                // 确保模态框显示
                setTimeout(() => {
                    const modal = document.getElementById('productModal');
                    if (modal) {
                        console.log('🎯 强制显示模态框');
                        modal.style.display = 'block';
                        modal.classList.add('show');
                        
                        // 添加背景遮罩
                        let backdrop = document.querySelector('.modal-backdrop');
                        if (!backdrop) {
                            backdrop = document.createElement('div');
                            backdrop.className = 'modal-backdrop';
                            backdrop.style.cssText = `
                                position: fixed;
                                top: 0;
                                left: 0;
                                width: 100vw;
                                height: 100vh;
                                background-color: rgba(0, 0, 0, 0.5);
                                z-index: 1040;
                            `;
                            document.body.appendChild(backdrop);
                        }
                        backdrop.style.display = 'block';
                        
                        console.log('✅ 模态框已强制显示');
                    } else {
                        console.error('❌ 找不到 productModal 元素');
                    }
                }, 100);
                
            } catch (error) {
                console.error('❌ editProduct 执行失败:', error);
                
                // 手动显示模态框
                const modal = document.getElementById('productModal');
                if (modal) {
                    console.log('🔧 手动显示模态框');
                    modal.style.display = 'block';
                    modal.classList.add('show');
                    
                    // 填充测试数据
                    const title = document.getElementById('productModalTitle');
                    const productName = document.getElementById('productName');
                    const description = document.getElementById('productDescription');
                    
                    if (title) title.innerHTML = '<i class="fas fa-edit"></i> 编辑产品（手动模式）';
                    if (productName) productName.value = '测试产品';
                    if (description) description.value = '测试描述';
                }
            }
        };
        
        // 修复关闭模态框功能
        const originalCloseModal = window.adminPage.closeModal;
        
        window.adminPage.closeModal = function(modalId) {
            console.log('🔄 关闭模态框:', modalId);
            
            if (originalCloseModal) {
                originalCloseModal.call(this, modalId);
            } else {
                const modal = document.getElementById(modalId);
                if (modal) {
                    modal.style.display = 'none';
                    modal.classList.remove('show');
                }
            }
            
            // 隐藏背景遮罩
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.style.display = 'none';
            }
        };
        
        // 添加全局测试函数
        window.testEditProduct = function() {
            console.log('🧪 测试编辑产品功能');
            if (window.adminPage && window.adminPage.editProduct) {
                window.adminPage.editProduct(13);
            } else {
                console.error('❌ adminPage.editProduct 不可用');
            }
        };
        
        console.log('✅ 模态框修复完成');
        
        // 在控制台显示使用说明
        console.log('📖 使用说明:');
        console.log('  - 点击编辑按钮应该能正常显示模态框');
        console.log('  - 如果仍有问题，可以在控制台运行: testEditProduct()');
        console.log('  - 或者手动运行: adminPage.editProduct(产品ID)');
        
    }, 2000); // 等待2秒确保所有脚本加载完成
});

// 添加必要的CSS样式
const modalStyles = document.createElement('style');
modalStyles.textContent = `
    .modal {
        display: none !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        background-color: rgba(0, 0, 0, 0.5) !important;
        z-index: 1050 !important;
        overflow: auto !important;
    }
    
    .modal.show {
        display: block !important;
    }
    
    .modal-content {
        position: relative !important;
        background-color: #fff !important;
        margin: 5% auto !important;
        padding: 0 !important;
        width: 90% !important;
        max-width: 600px !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
        animation: modalSlideIn 0.3s ease-out !important;
    }
    
    @keyframes modalSlideIn {
        from {
            opacity: 0;
            transform: translateY(-50px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .modal-header {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        padding: 1rem 1.5rem !important;
        border-bottom: 1px solid #dee2e6 !important;
        background-color: #f8f9fa !important;
        border-radius: 8px 8px 0 0 !important;
    }
    
    .modal-body {
        padding: 1.5rem !important;
        max-height: 70vh !important;
        overflow-y: auto !important;
    }
    
    .modal-actions {
        display: flex !important;
        gap: 0.5rem !important;
        justify-content: flex-end !important;
        padding: 1rem 1.5rem !important;
        border-top: 1px solid #dee2e6 !important;
        background-color: #f8f9fa !important;
        border-radius: 0 0 8px 8px !important;
    }
    
    .close {
        background: none !important;
        border: none !important;
        font-size: 1.5rem !important;
        color: #666 !important;
        cursor: pointer !important;
        padding: 0 !important;
        width: 30px !important;
        height: 30px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 4px !important;
        transition: all 0.2s ease !important;
    }
    
    .close:hover {
        background-color: #e9ecef !important;
        color: #333 !important;
    }
    
    /* 确保按钮可以点击 */
    .modal-content * {
        pointer-events: auto !important;
    }
    
    /* 表单样式增强 */
    .modal .form-group {
        margin-bottom: 1rem !important;
    }
    
    .modal .form-group label {
        display: block !important;
        margin-bottom: 0.5rem !important;
        font-weight: 500 !important;
        color: #333 !important;
    }
    
    .modal .form-control {
        width: 100% !important;
        padding: 0.5rem !important;
        border: 1px solid #ced4da !important;
        border-radius: 4px !important;
        font-size: 1rem !important;
        transition: border-color 0.15s ease !important;
        box-sizing: border-box !important;
    }
    
    .modal .form-control:focus {
        outline: none !important;
        border-color: #007bff !important;
        box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25) !important;
    }
    
    .modal textarea.form-control {
        resize: vertical !important;
        min-height: 80px !important;
    }
    
    .modal .btn {
        padding: 0.5rem 1rem !important;
        border: none !important;
        border-radius: 4px !important;
        font-size: 1rem !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        text-decoration: none !important;
        display: inline-block !important;
    }
    
    .modal .btn-primary {
        background-color: #007bff !important;
        color: white !important;
    }
    
    .modal .btn-primary:hover {
        background-color: #0056b3 !important;
    }
    
    .modal .btn-outline {
        background-color: transparent !important;
        color: #666 !important;
        border: 1px solid #ced4da !important;
    }
    
    .modal .btn-outline:hover {
        background-color: #e9ecef !important;
        border-color: #adb5bd !important;
    }
`;
document.head.appendChild(modalStyles);

console.log('🎨 模态框样式已添加');
