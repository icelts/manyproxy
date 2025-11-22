// 调试模态框功能的脚本
console.log('🔍 开始调试模态框功能...');

// 检查adminPage是否已初始化
function checkAdminPage() {
    if (typeof adminPage === 'undefined') {
        console.error('❌ adminPage 未定义');
        return false;
    }
    
    if (!adminPage.editProduct) {
        console.error('❌ adminPage.editProduct 方法不存在');
        return false;
    }
    
    console.log('✅ adminPage 已正确初始化');
    return true;
}

// 检查模态框元素是否存在
function checkModalElements() {
    const modal = document.getElementById('productModal');
    const modalTitle = document.getElementById('productModalTitle');
    const modalBody = document.querySelector('#productModal .modal-body');
    
    console.log('📋 检查模态框元素:');
    console.log('  - productModal:', modal ? '✅ 存在' : '❌ 不存在');
    console.log('  - productModalTitle:', modalTitle ? '✅ 存在' : '❌ 不存在');
    console.log('  - modalBody:', modalBody ? '✅ 存在' : '❌ 不存在');
    
    if (modal) {
        console.log('  - modal.style.display:', modal.style.display);
        console.log('  - modal.classList:', modal.classList.toString());
    }
    
    return !!(modal && modalTitle && modalBody);
}

// 测试编辑产品功能
function testEditProduct() {
    console.log('🧪 测试编辑产品功能...');
    
    // 模拟产品ID
    const testProductId = 13;
    
    try {
        // 调用编辑方法
        adminPage.editProduct(testProductId);
        console.log('✅ editProduct 方法调用成功');
        
        // 检查模态框是否显示
        setTimeout(() => {
            const modal = document.getElementById('productModal');
            if (modal && modal.style.display === 'block') {
                console.log('✅ 模态框已显示');
            } else {
                console.error('❌ 模态框未显示');
                console.log('  - modal.style.display:', modal ? modal.style.display : 'modal不存在');
            }
        }, 100);
        
    } catch (error) {
        console.error('❌ editProduct 调用失败:', error);
    }
}

// 手动显示模态框
function showModalManually() {
    console.log('🔧 手动显示模态框...');
    
    const modal = document.getElementById('productModal');
    if (modal) {
        modal.style.display = 'block';
        modal.classList.add('show');
        
        // 添加backdrop
        let backdrop = document.querySelector('.modal-backdrop');
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop';
            document.body.appendChild(backdrop);
        }
        backdrop.style.display = 'block';
        
        console.log('✅ 模态框手动显示成功');
        
        // 填充测试数据
        const title = document.getElementById('productModalTitle');
        const productName = document.getElementById('productName');
        const description = document.getElementById('productDescription');
        
        if (title) title.innerHTML = '<i class="fas fa-edit"></i> 测试编辑产品';
        if (productName) productName.value = '测试产品名称';
        if (description) description.value = '测试产品描述';
        
    } else {
        console.error('❌ 找不到productModal元素');
    }
}

// 手动隐藏模态框
function hideModalManually() {
    console.log('🔧 手动隐藏模态框...');
    
    const modal = document.getElementById('productModal');
    const backdrop = document.querySelector('.modal-backdrop');
    
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
    
    if (backdrop) {
        backdrop.style.display = 'none';
    }
    
    console.log('✅ 模态框手动隐藏成功');
}

// 检查CSS样式
function checkModalStyles() {
    console.log('🎨 检查模态框CSS样式...');
    
    const modal = document.getElementById('productModal');
    if (!modal) {
        console.error('❌ 找不到模态框元素');
        return;
    }
    
    const styles = window.getComputedStyle(modal);
    console.log('模态框样式:');
    console.log('  - display:', styles.display);
    console.log('  - position:', styles.position);
    console.log('  - z-index:', styles.zIndex);
    console.log('  - background:', styles.backgroundColor);
    console.log('  - visibility:', styles.visibility);
}

// 添加必要的CSS样式
function addModalStyles() {
    console.log('🎨 添加模态框CSS样式...');
    
    const styleSheet = document.createElement('style');
    styleSheet.textContent = `
        /* 模态框基础样式 */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 1050;
            overflow: auto;
        }
        
        .modal.show {
            display: block !important;
        }
        
        .modal-content {
            position: relative;
            background-color: #fff;
            margin: 5% auto;
            padding: 0;
            width: 90%;
            max-width: 600px;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            animation: modalSlideIn 0.3s ease-out;
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
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.5rem;
            border-bottom: 1px solid #dee2e6;
            background-color: #f8f9fa;
            border-radius: 8px 8px 0 0;
        }
        
        .modal-header h4 {
            margin: 0;
            color: #333;
            font-size: 1.25rem;
            font-weight: 600;
        }
        
        .modal-body {
            padding: 1.5rem;
            max-height: 70vh;
            overflow-y: auto;
        }
        
        .modal-actions {
            display: flex;
            gap: 0.5rem;
            justify-content: flex-end;
            padding: 1rem 1.5rem;
            border-top: 1px solid #dee2e6;
            background-color: #f8f9fa;
            border-radius: 0 0 8px 8px;
        }
        
        .close {
            background: none;
            border: none;
            font-size: 1.5rem;
            color: #666;
            cursor: pointer;
            padding: 0;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            transition: all 0.2s ease;
        }
        
        .close:hover {
            background-color: #e9ecef;
            color: #333;
        }
        
        /* 确保按钮可以点击 */
        .modal-content * {
            pointer-events: auto;
        }
        
        /* 表单样式增强 */
        .modal .form-group {
            margin-bottom: 1rem;
        }
        
        .modal .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #333;
        }
        
        .modal .form-control {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 1rem;
            transition: border-color 0.15s ease;
        }
        
        .modal .form-control:focus {
            outline: none;
            border-color: #007bff;
            box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
        }
        
        .modal textarea.form-control {
            resize: vertical;
            min-height: 80px;
        }
        
        /* 按钮样式 */
        .modal .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .modal .btn-primary {
            background-color: #007bff;
            color: white;
        }
        
        .modal .btn-primary:hover {
            background-color: #0056b3;
        }
        
        .modal .btn-outline {
            background-color: transparent;
            color: #666;
            border: 1px solid #ced4da;
        }
        
        .modal .btn-outline:hover {
            background-color: #e9ecef;
            border-color: #adb5bd;
        }
    `;
    
    document.head.appendChild(styleSheet);
    console.log('✅ 模态框CSS样式已添加');
}

// 运行所有调试检查
function runDebugChecks() {
    console.log('🚀 开始运行模态框调试检查...');
    console.log('=' * 50);
    
    // 检查基本元素
    const elementsOk = checkModalElements();
    
    // 检查adminPage
    const adminPageOk = checkAdminPage();
    
    // 添加CSS样式
    addModalStyles();
    
    // 检查样式
    checkModalStyles();
    
    console.log('=' * 50);
    
    if (elementsOk && adminPageOk) {
        console.log('✅ 基础检查通过，可以测试编辑功能');
        
        // 提供手动测试按钮
        createDebugButtons();
        
    } else {
        console.error('❌ 基础检查失败，请检查页面加载');
    }
}

// 创建调试按钮
function createDebugButtons() {
    const debugPanel = document.createElement('div');
    debugPanel.id = 'debug-panel';
    debugPanel.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        background: white;
        border: 2px solid #007bff;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        font-family: Arial, sans-serif;
    `;
    
    debugPanel.innerHTML = `
        <h4 style="margin: 0 0 0.5rem 0; color: #007bff;">🔧 模态框调试面板</h4>
        <button onclick="showModalManually()" style="margin: 0.25rem; padding: 0.5rem; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">显示模态框</button>
        <button onclick="hideModalManually()" style="margin: 0.25rem; padding: 0.5rem; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">隐藏模态框</button>
        <button onclick="testEditProduct()" style="margin: 0.25rem; padding: 0.5rem; background: #ffc107; color: black; border: none; border-radius: 4px; cursor: pointer;">测试编辑功能</button>
        <button onclick="checkModalStyles()" style="margin: 0.25rem; padding: 0.5rem; background: #17a2b8; color: white; border: none; border-radius: 4px; cursor: pointer;">检查样式</button>
    `;
    
    document.body.appendChild(debugPanel);
    console.log('✅ 调试面板已创建');
}

// 页面加载完成后运行调试
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runDebugChecks);
} else {
    runDebugChecks();
}

// 导出调试函数到全局作用域
window.showModalManually = showModalManually;
window.hideModalManually = hideModalManually;
window.testEditProduct = testEditProduct;
window.checkModalStyles = checkModalStyles;

console.log('🔍 模态框调试脚本已加载');
