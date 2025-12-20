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
        
        # 仅保留允许的 USDT 网络（例如 TRON / ETH / BSC），其他币种不暴露给前端
        self.allowed_currency = "USDT"
        self.allowed_networks = {"TRON", "ETH", "BSC"}
        # 配置映射，network_api 为 Cryptomus 接口需要的大写网络标识
        self.supported_currencies = {
            'USDT': {
                'name': 'Tether',
                'symbol': '₮',
                # 默认展示网络名（前端可覆盖），network_api 在构建请求时按用户选择的网络填充
                'network': 'TRC20',
                'network_api': None
            }
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
        callback_url: Optional[str] = None,
        network: Optional[str] = None
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
        # 生产环境不再静默回退到 mock，未配置直接报错
        if not self.use_cryptomus:
            raise RuntimeError("Cryptomus 未配置，无法创建真实支付")
        
        # 直接调用真实 Cryptomus，如有异常上抛交由上层处理
        return await self._create_cryptomus_payment(amount, currency, payment_id, None, callback_url, network)
    
    async def _create_cryptomus_payment(self, amount: float, currency: str, payment_id: str, user_id: int, callback_url: Optional[str] = None, network: Optional[str] = None) -> Dict[str, Any]:
        """创建Cryptomus真实支付"""
        # 生成支付ID
        payment_id = payment_id or f"pay_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"

        # 设置回调URL
        if not callback_url:
            callback_url = settings.CRYPTOMUS_WEBHOOK_URL or f"https://your-domain.com/api/v1/orders/payments/cryptomus-webhook"

        # 获取网络信息
        currency_info = self.supported_currencies.get(currency.upper())
        if not currency_info:
            raise ValueError(f"Unsupported currency: {currency}")

        # 根据订单指定的网络，缺省回退 TRON
        network = (network or '').upper() or 'TRON'
        if network not in self.allowed_networks:
            raise ValueError(f"Unsupported network for USDT: {network}")

        # 调用Cryptomus API创建支付
        async with get_cryptomus_client() as client:
            # 直接以目标加密货币计价，避免 to_currency 触发"Not found service to_currency"
            cryptomus_response = await client.create_payment(
                amount=amount,
                currency=currency.upper(),  # 发起订单使用目标加密货币
                order_id=payment_id,
                currency_from=None,  # 不做法币换算
                to_currency=None,
                url_callback=callback_url,
                lifetime=1800,  # 30分钟有效期，避免立即过期
                network=network
            )

        # 解析Cryptomus响应（允许 state=0 但带 result 的情况）
        if cryptomus_response.get('state') not in (0, 1):
            raise Exception(f"Cryptomus payment creation failed: {cryptomus_response.get('message', 'Unknown error')}")

        result = cryptomus_response.get('result', {})
        if not result:
            raise Exception("Cryptomus payment creation returned empty result")

        required_confirmations = 12 if network in {"ETH", "BSC"} else 1

        # 转换为标准格式
        payment_info = {
            'payment_id': result.get('uuid', payment_id),
            'order_id': result.get('order_id', payment_id),
            'wallet_address': result.get('address'),
            'address_qr_code': result.get('address_qr_code'),
            'crypto_amount': result.get('amount', '0'),
            'crypto_currency': result.get('currency', currency.upper()),
            'usd_amount': str(amount),
            'network': result.get('network', currency_info['network']),
            'payment_url': result.get('url'),
            'status': self._convert_cryptomus_status(result.get('payment_status', 'check')),
            'confirmations': 0,
            'required_confirmations': required_confirmations,
            'expires_at': datetime.fromtimestamp(result.get('expired_at', 0)).isoformat() if result.get('expired_at') else None,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'provider': 'cryptomus',
            'merchant_uuid': settings.CRYPTOMUS_MERCHANT_UUID,
            # 额外保存 Cryptomus 返回的 uuid，方便后续状态查询
            'cryptomus_uuid': result.get('uuid')
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
                # 优先使用 Cryptomus 返回的 uuid；否则使用下单时传入的 order_id（即我方 payment_id）
                lookup_kwargs = {}
                if cached_payment.get('cryptomus_uuid'):
                    lookup_kwargs['payment_id'] = cached_payment['cryptomus_uuid']
                else:
                    lookup_kwargs['order_id'] = cached_payment.get('order_id') or payment_id

                async with get_cryptomus_client() as client:
                    response = await client.get_payment_info(**lookup_kwargs)
                
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
        生成支付二维码（仅在Cryptomus未返回时使用）
        
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
        
        # 使用外部QR码服务生成二维码（仅在Cryptomus未返回二维码时使用）
        import urllib.parse
        encoded_qr_data = urllib.parse.quote(qr_data, safe='')
        return f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={encoded_qr_data}"
    
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
        if not self.use_cryptomus:
            raise RuntimeError("Cryptomus 未配置，无法获取可用币种")

        # 直接从 Cryptomus 拉取，失败则抛出异常（不做本地兜底）
        async with get_cryptomus_client() as client:
            response = await client.get_services()

        if response.get('state') not in (0, 1):
            raise RuntimeError(response.get('message', 'Failed to fetch Cryptomus services'))

        services = response.get('result', [])
        if not services:
            raise RuntimeError("Cryptomus returned empty services list")
        currencies = []

        allowed_networks_upper = {n.upper() for n in self.allowed_networks}

        for service in services:
            currency_code = service.get('currency')
            network_code = (service.get('network') or '').upper()

            # 仅保留允许的币种和网络
            if currency_code != self.allowed_currency or network_code not in allowed_networks_upper:
                continue

            currency_info = self.supported_currencies[currency_code]
            # 确定展示的网络名称
            display_network = service.get('network', currency_info['network'])
            required_conf = 12 if network_code in {"ETH", "BSC"} else 1

            currencies.append({
                'code': currency_code,
                'name': currency_info['name'],
                'symbol': currency_info['symbol'],
                'network': display_network,
                'network_code': network_code,
                'available': service.get('is_available', True),
                'limit': service.get('limit', {}),
                'commission': service.get('commission', {}),
                # USDT 固定汇率为 1，网络确认数按链路设定
                'rate': 1.0,
                'confirmations': required_conf
            })

        if not currencies:
            raise RuntimeError("No allowed USDT networks available from Cryptomus")

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
