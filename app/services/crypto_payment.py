"""
加密货币支付服务
模拟加密货币支付处理，实际项目中需要集成真实的支付网关
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional


class CryptoPaymentService:
    """加密货币支付服务"""
    
    def __init__(self):
        # 模拟的支付地址配置
        self.wallet_addresses = {
            'BTC': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            'ETH': '0x742d35Cc6634C0532925a3b8D4C9db96C4b4Db45',
            'USDT': '0x742d35Cc6634C0532925a3b8D4C9db96C4b4Db45',
            'USDC': '0x742d35Cc6634C0532925a3b8D4C9db96C4b4Db45'
        }
        
        # 模拟的汇率（实际项目中应该从实时汇率API获取）
        self.exchange_rates = {
            'BTC': 45000.0,  # 1 BTC = $45,000
            'ETH': 3000.0,   # 1 ETH = $3,000
            'USDT': 1.0,     # 1 USDT = $1
            'USDC': 1.0      # 1 USDC = $1
        }
        
        # 模拟的交易确认要求
        self.confirmation_requirements = {
            'BTC': 1,
            'ETH': 12,
            'USDT': 12,
            'USDC': 12
        }
        # 内部支付会话存储
        self._payments: Dict[str, Dict] = {}
    
    def create_payment(self, amount: float, currency: str, payment_id: Optional[str] = None) -> Dict:
        """
        创建支付订单
        
        Args:
            amount: 支付金额（USD）
            currency: 加密货币类型
            
        Returns:
            支付信息字典
        """
        if currency not in self.wallet_addresses:
            raise ValueError(f"Unsupported currency: {currency}")
        
        # 生成支付ID
        payment_id = payment_id or str(uuid.uuid4())
        
        now = datetime.utcnow()
        # 计算需要的加密货币数量
        crypto_amount = self.calculate_crypto_amount(amount, currency)
        
        # 生成支付地址（实际项目中应该为每个订单生成唯一地址）
        wallet_address = self.wallet_addresses[currency]
        
        # 设置过期时间（30分钟）
        expires_at = now + timedelta(minutes=30)
        
        # 生成支付监控URL
        monitor_url = f"/api/v1/orders/payments/{payment_id}/monitor"
        
        payment_info = {
            'payment_id': payment_id,
            'wallet_address': wallet_address,
            'crypto_amount': crypto_amount,
            'crypto_currency': currency,
            'usd_amount': amount,
            'expires_at': expires_at.isoformat(),
            'monitor_url': monitor_url,
            'qr_code_url': f"/api/v1/orders/payments/{payment_id}/qrcode",
            'status': 'pending',
            'confirmations': 0,
            'required_confirmations': self.confirmation_requirements[currency],
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        }
        # 持久化支付会话
        self._payments[payment_id] = {
            **payment_info,
            'expires_at': expires_at,  # 保留datetime用于内部计算
            'created_at': now,
            'updated_at': now
        }
        return payment_info
    
    def calculate_crypto_amount(self, usd_amount: float, currency: str) -> str:
        """
        计算需要的加密货币数量
        
        Args:
            usd_amount: USD金额
            currency: 加密货币类型
            
        Returns:
            加密货币数量字符串
        """
        if currency not in self.exchange_rates:
            raise ValueError(f"Unsupported currency: {currency}")
        
        rate = self.exchange_rates[currency]
        crypto_amount = Decimal(str(usd_amount)) / Decimal(str(rate))
        
        # 根据不同货币设置精度
        if currency == 'BTC':
            return f"{crypto_amount:.8f}"
        elif currency in ['ETH', 'USDT', 'USDC']:
            return f"{crypto_amount:.6f}"
        else:
            return f"{crypto_amount:.6f}"
    
    def verify_payment(self, payment_id: str) -> Dict:
        """
        查询当前已知的支付状态
        """
        return self._serialize_payment(self._payments.get(payment_id), payment_id)

    def get_payment_status(self, payment_id: str) -> Dict:
        """
        获取支付状态
        """
        return self._serialize_payment(self._payments.get(payment_id), payment_id)

    def update_payment_status(
        self,
        payment_id: str,
        status: str,
        transaction_hash: Optional[str] = None,
        confirmations: int = 0
    ) -> Dict:
        """
        更新内部支付记录状态
        """
        payment = self._payments.setdefault(payment_id, {'payment_id': payment_id})
        payment['status'] = status
        payment['confirmations'] = confirmations
        payment['transaction_hash'] = transaction_hash
        payment['updated_at'] = datetime.utcnow()
        return self._serialize_payment(payment, payment_id, include_datetime=False)

    def _serialize_payment(self, payment: Optional[Dict], payment_id: str, include_datetime: bool = True) -> Dict:
        if not payment:
            return {
                'payment_id': payment_id,
                'status': 'not_found'
            }
        data = dict(payment)
        if include_datetime:
            for date_field in ("expires_at", "created_at", "updated_at"):
                value = data.get(date_field)
                if isinstance(value, datetime):
                    data[date_field] = value.isoformat()
        else:
            # ensure datetime objects are dropped when not needed
            for date_field in ("expires_at", "created_at", "updated_at"):
                value = data.get(date_field)
                if isinstance(value, datetime):
                    data[date_field] = value.isoformat()
        data.setdefault(
            'required_confirmations',
            self.confirmation_requirements.get(data.get('crypto_currency', 'BTC'), 1)
        )
        return data

    def generate_qr_code(self, payment_id: str, wallet_address: str, crypto_amount: str, currency: str) -> str:
        """
        生成支付二维码
        
        Args:
            payment_id: 支付ID
            wallet_address: 钱包地址
            crypto_amount: 加密货币数量
            currency: 加密货币类型
            
        Returns:
            二维码数据URL
        """
        # 生成支付URI
        if currency == 'BTC':
            qr_data = f"bitcoin:{wallet_address}?amount={crypto_amount}"
        elif currency in ['ETH', 'USDT', 'USDC']:
            qr_data = f"ethereum:{wallet_address}?value={int(float(crypto_amount) * 1e18)}"
        else:
            qr_data = wallet_address
        
        # 实际项目中应该使用二维码库生成二维码图片
        # 这里返回模拟的二维码数据
        return f"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    def cancel_payment(self, payment_id: str) -> Dict:
        """
        取消支付
        
        Args:
            payment_id: 支付ID
            
        Returns:
            取消结果
        """
        cancelled = self.update_payment_status(
            payment_id,
            status='cancelled',
            confirmations=0
        )
        cancelled['cancelled_at'] = datetime.utcnow().isoformat()
        return cancelled
    
    def get_supported_currencies(self) -> Dict:
        """
        获取支持的加密货币列表
        
        Returns:
            支持的货币信息
        """
        return {
            'currencies': [
                {
                    'code': 'BTC',
                    'name': 'Bitcoin',
                    'symbol': '₿',
                    'rate': self.exchange_rates['BTC'],
                    'confirmations': self.confirmation_requirements['BTC']
                },
                {
                    'code': 'ETH',
                    'name': 'Ethereum',
                    'symbol': 'Ξ',
                    'rate': self.exchange_rates['ETH'],
                    'confirmations': self.confirmation_requirements['ETH']
                },
                {
                    'code': 'USDT',
                    'name': 'Tether',
                    'symbol': '₮',
                    'rate': self.exchange_rates['USDT'],
                    'confirmations': self.confirmation_requirements['USDT']
                },
                {
                    'code': 'USDC',
                    'name': 'USD Coin',
                    'symbol': '$',
                    'rate': self.exchange_rates['USDC'],
                    'confirmations': self.confirmation_requirements['USDC']
                }
            ]
        }
    
    def update_exchange_rates(self) -> Dict:
        """
        更新汇率（模拟）
        
        实际项目中应该从汇率API获取实时汇率
        """
        # 模拟汇率波动
        import random
        
        for currency in self.exchange_rates:
            if currency != 'USDT' and currency != 'USDC':
                # 模拟±5%的汇率波动
                current_rate = self.exchange_rates[currency]
                change = random.uniform(-0.05, 0.05)
                new_rate = current_rate * (1 + change)
                self.exchange_rates[currency] = round(new_rate, 2)
        
        return self.exchange_rates
    
    def validate_address(self, address: str, currency: str) -> bool:
        """
        验证钱包地址格式
        
        Args:
            address: 钱包地址
            currency: 加密货币类型
            
        Returns:
            地址是否有效
        """
        # 简单的地址格式验证
        # 实际项目中应该使用相应的地址验证库
        
        if currency == 'BTC':
            # 比特币地址验证（简化版）
            return len(address) >= 26 and len(address) <= 35 and address.startswith(('1', '3', 'bc1'))
        elif currency in ['ETH', 'USDT', 'USDC']:
            # 以太坊地址验证（简化版）
            return address.startswith('0x') and len(address) == 42
        
        return False

# 全局支付服务实例
crypto_payment_service = CryptoPaymentService()
