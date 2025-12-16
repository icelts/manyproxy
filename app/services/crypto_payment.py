"""
加密货币支付服务
集成Cryptomus支付网关，支持真实的加密货币支付处理
"""

import uuid
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, Any

from app.services.cryptomus_client import get_cryptomus_client
from app.core.config import settings
from app.utils.cache import CacheService

logger = logging.getLogger(__name__)


class CryptoPaymentService:
    """加密货币支付服务 - 集成Cryptomus"""
    
    def __init__(self):
        self.use_cryptomus = bool(settings.CRYPTOMUS_API_KEY and settings.CRYPTOMUS_MERCHANT_UUID)
        
        # 支持的加密货币配置
        self.supported_currencies = {
            'BTC': {'name': 'Bitcoin', 'symbol': '₿', 'network': 'BTC'},
            'ETH': {'name': 'Ethereum', 'symbol': 'Ξ', 'network': 'ETH'},
            'USDT': {'name': 'Tether', 'symbol': '₮', 'network': 'TRC20'},
            'USDC': {'name': 'USD Coin', 'symbol': '$', 'network': 'TRC20'},
            'TRX': {'name': 'Tron', 'symbol': 'TRX', 'network': 'TRX'},
            'LTC': {'name': 'Litecoin', 'symbol': 'Ł', 'network': 'LTC'},
            'DASH': {'name': 'Dash', 'symbol': 'Đ', 'network': 'DASH'}
        }
        
        # 内部支付会话存储（用于缓存和状态跟踪）
        self._payments: Dict[str, Dict] = {}
        self.cache_ttl_seconds = 2 * 60 * 60  # 2小时缓存

    def _cache_key(self, payment_id: str) -> str:
        return f"payment:{payment_id}"

    async def _save_payment(self, payment_id: str, data: Dict[str, Any]) -> None:
        """保存支付信息到内存+Redis"""
        self._payments[payment_id] = data
        await CacheService.set(self._cache_key(payment_id), data, ttl=self.cache_ttl_seconds)

    async def _load_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """优先从Redis读取，再回退内存"""
        cached = await CacheService.get(self._cache_key(payment_id))
        if cached:
            self._payments[payment_id] = cached
            return cached
        return self._payments.get(payment_id)

    async def get_cached_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """获取已存储的支付信息（不调用上游）"""
        return await self._load_payment(payment_id)

    def _is_final_status(self, status: str) -> bool:
        return status in {'confirmed', 'paid', 'cancelled', 'expired', 'failed'}
    
    async def create_payment(
        self, 
        amount: float, 
        currency: str, 
        payment_id: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建支付订单
        
        Args:
            amount: 支付金额（USD）
            currency: 加密货币类型
            payment_id: 自定义支付ID
            callback_url: 回调URL
            
        Returns:
            支付信息字典
        """
        if not self.use_cryptomus:
            raise RuntimeError("Cryptomus 未配置，无法创建真实支付")
        
        # 生成支付ID
        payment_id = payment_id or f"pay_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"

        # 设置回调URL
        if not callback_url:
            callback_url = settings.CRYPTOMUS_WEBHOOK_URL or f"https://your-domain.com/api/v1/orders/payments/cryptomus-webhook"

        # 获取网络信息
        currency_info = self.supported_currencies.get(currency.upper())
        if not currency_info:
            raise ValueError(f"Unsupported currency: {currency}")

        # 调用Cryptomus API创建支付
        async with get_cryptomus_client() as client:
            cryptomus_response = await client.create_payment(
                amount=amount,
                currency="USD",
                order_id=payment_id,
                currency_from="USD",
                to_currency=currency.upper(),
                url_callback=callback_url,
                lifetime=3600,  # 1小时有效期
                network=currency_info['network']
            )

        # 解析Cryptomus响应
        if cryptomus_response.get('state') != 1:
            raise Exception(f"Cryptomus payment creation failed: {cryptomus_response.get('message', 'Unknown error')}")

        result = cryptomus_response.get('result', {})

        # 转换为标准格式
        payment_info = {
            'payment_id': result.get('uuid', payment_id),
            'order_id': result.get('order_id', payment_id),
            'wallet_address': result.get('address'),
            'crypto_amount': result.get('amount', '0'),
            'crypto_currency': result.get('currency', currency.upper()),
            'usd_amount': str(amount),
            'network': result.get('network', currency_info['network']),
            'payment_url': result.get('url'),
            'status': self._convert_cryptomus_status(result.get('payment_status', 'check')),
            'confirmations': 0,
            'required_confirmations': self._get_required_confirmations(currency),
            'expires_at': datetime.fromtimestamp(result.get('expired_at', 0)).isoformat() if result.get('expired_at') else None,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'provider': 'cryptomus',
            'merchant_uuid': settings.CRYPTOMUS_MERCHANT_UUID
        }

        # 缓存支付信息（内存 + Redis）
        await self._save_payment(payment_id, {**payment_info, 'cryptomus_data': result})

        logger.info(f"Created Cryptomus payment: {payment_id} for {amount} USD")
        return payment_info
    
    async def _create_mock_payment(self, amount: float, currency: str, payment_id: Optional[str] = None) -> Dict[str, Any]:
        """创建模拟支付（回退方案）"""
        payment_id = payment_id or f"mock_{int(datetime.now().timestamp())}"
        
        currency_info = self.supported_currencies.get(currency.upper())
        if not currency_info:
            raise ValueError(f"Unsupported currency: {currency}")
        
        # 模拟汇率计算
        exchange_rates = {
            'BTC': 45000.0, 'ETH': 3000.0, 'USDT': 1.0, 'USDC': 1.0,
            'TRX': 0.1, 'LTC': 100.0, 'DASH': 50.0
        }
        
        rate = exchange_rates.get(currency.upper(), 1.0)
        crypto_amount = Decimal(str(amount)) / Decimal(str(rate))
        
        # 模拟钱包地址
        mock_addresses = {
            'BTC': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            'ETH': '0x742d35Cc6634C0532925a3b8D4C9db96C4b4Db45',
            'USDT': '0x742d35Cc6634C0532925a3b8D4C9db96C4b4Db45',
            'USDC': '0x742d35Cc6634C0532925a3b8D4C9db96C4b4Db45',
            'TRX': 'TXguLRFtrAFrEDA17WuPfrxB84jVzJcNNV',
            'LTC': 'LMYiL9teWJ1nFz4uGQqAqUWkU5vfNqLh',
            'DASH': 'XwMqCvuJfVsFVLgV8AaJy2hYwpJE2bjSM'
        }
        
        payment_info = {
            'payment_id': payment_id,
            'wallet_address': mock_addresses.get(currency.upper()),
            'crypto_amount': f"{crypto_amount:.8f}" if currency.upper() == 'BTC' else f"{crypto_amount:.6f}",
            'crypto_currency': currency.upper(),
            'usd_amount': str(amount),
            'network': currency_info['network'],
            'status': 'pending',
            'confirmations': 0,
            'required_confirmations': self._get_required_confirmations(currency),
            'expires_at': (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'provider': 'mock',
            'merchant_uuid': settings.CRYPTOMUS_MERCHANT_UUID
        }
        
        # 缓存支付信息（内存 + Redis）
        await self._save_payment(payment_id, payment_info)
        
        return payment_info
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        获取支付状态
        
        Args:
            payment_id: 支付ID
            
        Returns:
            支付状态信息
        """
        # 先从缓存/Redis获取
        cached_payment = await self._load_payment(payment_id)
        if not cached_payment:
            return {'payment_id': payment_id, 'status': 'not_found'}
        
        # 如果是模拟支付，返回缓存状态
        if cached_payment.get('provider') == 'mock':
            return cached_payment
        
        # 如果是Cryptomus支付，查询实时状态
        if cached_payment.get('provider') == 'cryptomus' and self.use_cryptomus:
            try:
                async with get_cryptomus_client() as client:
                    response = await client.get_payment_info(payment_id=payment_id)
                
                if response.get('state') != 1:
                    logger.warning(f"Failed to get payment status: {response.get('message', 'Unknown error')}")
                    return cached_payment
                
                result = response.get('result', {})
                
                # 更新缓存状态
                updated_payment = {
                    **cached_payment,
                    'status': self._convert_cryptomus_status(result.get('payment_status', 'check')),
                    'confirmations': result.get('confirmations', cached_payment.get('confirmations', 0)),
                    'transaction_hash': result.get('txid'),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                await self._save_payment(payment_id, updated_payment)
                return updated_payment
                
            except Exception as e:
                logger.error(f"Failed to get Cryptomus payment status: {str(e)}")
                return cached_payment
        
        return cached_payment
    
    async def update_payment_status(
        self,
        payment_id: str,
        status: str,
        transaction_hash: Optional[str] = None,
        confirmations: int = 0
    ) -> Dict[str, Any]:
        """
        更新支付状态（通常由webhook触发）
        
        Args:
            payment_id: 支付ID
            status: 新状态
            transaction_hash: 交易哈希
            confirmations: 确认数
            
        Returns:
            更新后的支付信息
        """
        payment = await self._load_payment(payment_id) or {'payment_id': payment_id}
        
        # 已是终态且状态未变化，直接返回（防重放）
        if self._is_final_status(payment.get('status', '')) and self._is_final_status(status) and status == payment.get('status'):
            return payment
        
        # 更新状态
        payment.update({
            'status': status,
            'confirmations': confirmations,
            'transaction_hash': transaction_hash,
            'updated_at': datetime.utcnow().isoformat()
        })
        
        # 缓存更新
        await self._save_payment(payment_id, payment)
        
        return payment
    
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
        if currency.upper() == 'BTC':
            qr_data = f"bitcoin:{wallet_address}?amount={crypto_amount}"
        elif currency.upper() in ['ETH', 'USDT', 'USDC']:
            # 转换为wei单位（对于ETH相关代币）
            if currency.upper() == 'ETH':
                qr_data = f"ethereum:{wallet_address}?value={int(float(crypto_amount) * 1e18)}"
            else:
                qr_data = f"ethereum:{wallet_address}"
        elif currency.upper() == 'TRX':
            qr_data = f"tron:{wallet_address}?amount={crypto_amount}"
        else:
            qr_data = wallet_address
        
        # 实际项目中应该使用二维码库生成二维码图片
        # 这里返回模拟的二维码数据
        return f"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        取消支付
        
        Args:
            payment_id: 支付ID
            
        Returns:
            取消结果
        """
        payment = self._payments.get(payment_id, {})
        payment.update({
            'status': 'cancelled',
            'cancelled_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        })
        
        await self._save_payment(payment_id, payment)
        return payment
    
    async def get_supported_currencies(self) -> Dict[str, Any]:
        """
        获取支持的加密货币列表
        
        Returns:
            支持的货币信息
        """
        if self.use_cryptomus:
            try:
                # 从Cryptomus获取实时服务列表
                async with get_cryptomus_client() as client:
                    response = await client.get_services()
                
                if response.get('state') == 1:
                    services = response.get('result', [])
                    currencies = []
                    
                    for service in services:
                        currency_code = service.get('currency')
                        if currency_code and currency_code in self.supported_currencies:
                            currency_info = self.supported_currencies[currency_code]
                            currencies.append({
                                'code': currency_code,
                                'name': currency_info['name'],
                                'symbol': currency_info['symbol'],
                                'network': service.get('network', currency_info['network']),
                                'available': service.get('is_available', True),
                                'limit': service.get('limit', {}),
                                'commission': service.get('commission', {})
                            })
                    
                    return {'currencies': currencies}
                    
            except Exception as e:
                logger.error(f"Failed to get Cryptomus services: {str(e)}")
        
        # 回退到默认货币列表
        currencies = []
        for code, info in self.supported_currencies.items():
            currencies.append({
                'code': code,
                'name': info['name'],
                'symbol': info['symbol'],
                'network': info['network'],
                'available': True,
                'rate': self._get_mock_rate(code),
                'confirmations': self._get_required_confirmations(code)
            })
        
        return {'currencies': currencies}
    
    def _convert_cryptomus_status(self, cryptomus_status: str) -> str:
        """转换Cryptomus状态到标准状态"""
        status_mapping = {
            'check': 'pending',
            'paid': 'confirmed',
            'paid_over': 'confirmed',
            'wrong_amount': 'failed',
            'wrong_currency': 'failed',
            'expired': 'expired',
            'cancelled': 'cancelled'
        }
        return status_mapping.get(cryptomus_status, 'pending')
    
    def _get_required_confirmations(self, currency: str) -> int:
        """获取所需确认数"""
        confirmation_requirements = {
            'BTC': 1,
            'ETH': 12,
            'USDT': 12,
            'USDC': 12,
            'TRX': 1,
            'LTC': 6,
            'DASH': 6
        }
        return confirmation_requirements.get(currency.upper(), 1)
    
    def _get_mock_rate(self, currency: str) -> float:
        """获取模拟汇率"""
        rates = {
            'BTC': 45000.0,
            'ETH': 3000.0,
            'USDT': 1.0,
            'USDC': 1.0,
            'TRX': 0.1,
            'LTC': 100.0,
            'DASH': 50.0
        }
        return rates.get(currency.upper(), 1.0)

    def update_exchange_rates(self) -> Dict[str, float]:
        """
        临时实现：返回内置模拟汇率（无外部请求，避免接口报500）
        """
        return {code: self._get_mock_rate(code) for code in self.supported_currencies.keys()}
    
    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        """
        验证webhook签名（使用 payout/webhook key + 原始body）
        """
        if not self.use_cryptomus:
            return False
        
        try:
            client = get_cryptomus_client()
            return client.verify_webhook_signature(raw_body, signature)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False


# 全局支付服务实例
crypto_payment_service = CryptoPaymentService()
