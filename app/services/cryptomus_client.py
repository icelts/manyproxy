"""
Cryptomus支付网关Python客户端
提供与Cryptomus API的完整集成
"""

import hashlib
import hmac
import json
import logging
import base64
from typing import Dict, Optional, Any, List
from decimal import Decimal
from urllib.parse import quote
import aiohttp
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class CryptomusClient:
    """Cryptomus支付网关客户端"""
    
    def __init__(self, api_key: str = None, merchant_uuid: str = None, base_url: str = None):
        """
        初始化Cryptomus客户端
        
        Args:
            api_key: Cryptomus API密钥
            merchant_uuid: 商户UUID
            base_url: API基础URL
        """
        self.api_key = api_key or settings.CRYPTOMUS_API_KEY
        self.merchant_uuid = merchant_uuid or settings.CRYPTOMUS_MERCHANT_UUID
        self.base_url = base_url or settings.CRYPTOMUS_BASE_URL
        
        if not self.api_key or not self.merchant_uuid:
            raise ValueError("CRYPTOMUS_API_KEY and CRYPTOMUS_MERCHANT_UUID must be set")
        
        self.session = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    def _generate_signature(self, raw_body: bytes, key: str) -> str:
        """
        Cryptomus 官方签名算法：
        1. 对 JSON 数据进行 base64 编码
        2. 拼接 API_KEY
        3. 计算 MD5 哈希
        
        官方文档：https://doc.cryptomus.com/merchant-api/request-format
        $sign = md5(base64_encode($data) . $API_KEY);
        """
        import base64
        
        # 解码原始body为JSON字符串
        json_str = raw_body.decode('utf-8')
        
        # 步骤1: 对JSON数据进行base64编码
        base64_data = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        
        # 步骤2: 拼接API_KEY
        sign_data = base64_data + key
        
        # 步骤3: 计算MD5哈希
        signature = hashlib.md5(sign_data.encode('utf-8')).hexdigest()
        
        return signature
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        allow_state_zero: bool = False,
    ) -> Dict[str, Any]:
        """
        发送HTTP请求到Cryptomus API
        
        Args:
            method: HTTP方法
            endpoint: API端点
            data: 请求数据
            
        Returns:
            API响应数据
            
        Raises:
            Exception: 请求失败时抛出异常
        """
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            url = endpoint
        else:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            'Content-Type': 'application/json',
            'merchant': self.merchant_uuid
        }
        
        # 准备请求数据
        if data is None:
            data = {}
        
        # 使用原始 JSON 作为签名输入
        raw_body = json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode("utf-8")
        headers['sign'] = self._generate_signature(raw_body, self.api_key)
        
        # 确保session存在
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.request(method, url, headers=headers, data=raw_body) as response:
                response_data = await response.json()
                
                # 检查响应状态
                if response.status != 200:
                    error_msg = response_data.get('message') if isinstance(response_data, dict) else None
                    error_msg = error_msg or str(response_data)
                    logger.error(f"Cryptomus API error: {response.status} - {error_msg}")
                    raise Exception(f"Cryptomus API error: {error_msg}")
                
                # 检查业务状态
                state = response_data.get('state') if isinstance(response_data, dict) else None
                if state is not None and state != 0:
                    error_msg = response_data.get('message') if isinstance(response_data, dict) else None
                    error_msg = error_msg or str(response_data)
                    logger.error(f"Cryptomus business error: {error_msg}")
                    raise Exception(f"Cryptomus business error: {error_msg}")
                
                return response_data
                
        except aiohttp.ClientError as e:
            logger.error(f"Cryptomus API request failed: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Cryptomus API unexpected error: {str(e)}")
            raise
    
    async def create_payment(
        self,
        amount: float,
        currency: str = "USD",
        order_id: str = None,
        currency_from: Optional[str] = None,
        network: str = None,
        url_callback: str = None,
        url_success: str = None,
        is_payment_multiple: bool = False,
        lifetime: int = 3600,
        to_currency: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建支付订单
        
        Args:
            amount: 支付金额
            currency: 货币类型
            order_id: 订单ID
            currency_from: 源货币
            network: 区块链网络
            url_callback: 回调URL
            url_success: 成功URL
            is_payment_multiple: 是否允许多次支付
            lifetime: 支付有效期（秒）
            to_currency: 目标货币
            
        Returns:
            支付信息
        """
        data = {
            'amount': str(amount),
            'currency': currency,
            'order_id': order_id or f"order_{int(datetime.now().timestamp())}",
            'is_payment_multiple': is_payment_multiple,
            'lifetime': lifetime
        }
        if currency_from:
            data['currency_from'] = currency_from
        
        # 添加可选参数
        if network:
            data['network'] = network
        if url_callback:
            data['url_callback'] = url_callback
        if url_success:
            data['url_success'] = url_success
        if to_currency:
            data['to_currency'] = to_currency
        
        return await self._make_request('POST', 'payment', data)
    
    async def get_payment_info(self, payment_id: str = None, order_id: str = None) -> Dict[str, Any]:
        """
        获取支付信息
        
        Args:
            payment_id: 支付ID
            order_id: 订单ID
            
        Returns:
            支付信息
        """
        data = {}
        if payment_id:
            data['uuid'] = payment_id
        elif order_id:
            data['order_id'] = order_id
        else:
            raise ValueError("Either payment_id or order_id must be provided")
        
        return await self._make_request('POST', 'payment/info', data)
    
    async def get_payment_history(
        self, 
        page: int = 1,
        limit: int = 50,
        order_id: str = None,
        status: str = None,
        start_date: str = None,
        end_date: str = None,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取支付历史
        
        Args:
            page: 页码
            limit: 每页数量
            order_id: 订单ID
            status: 支付状态
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            支付历史列表
        """
        data = {}
        if start_date:
            data['date_from'] = start_date
        if end_date:
            data['date_to'] = end_date

        endpoint = 'payment/list'
        if cursor:
            endpoint = f"payment/list?cursor={quote(cursor)}"

        return await self._make_request('POST', endpoint, data)
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        获取账户余额
        
        Returns:
            余额信息
        """
        return await self._make_request('POST', 'balance', {})
    
    async def get_services(self) -> Dict[str, Any]:
        """
        获取支持的服务列表
        
        Returns:
            服务列表
        """
        # 官方文档支付服务列表接口：/payment/services
        return await self._make_request('POST', 'payment/services', {}, allow_state_zero=True)
    
    async def create_static_wallet(
        self,
        currency: str,
        network: str,
        order_id: str = None,
        url_callback: str = None
    ) -> Dict[str, Any]:
        """
        ??????
        
        Args:
            currency: ????
            network: ??
            order_id: ??ID
            url_callback: ??URL
            
        Returns:
            ??????
        """
        data = {
            'currency': currency,
            'network': network
        }
        
        if order_id:
            data['order_id'] = order_id
        if url_callback:
            data['url_callback'] = url_callback
        
        return await self._make_request('POST', 'wallet', data)
    
    async def block_static_wallet(self, wallet_uuid: str) -> Dict[str, Any]:
        """
        ??????
        
        Args:
            wallet_uuid: ??UUID
            
        Returns:
            ????
        """
        data = {'uuid': wallet_uuid}
        return await self._make_request('POST', 'wallet/block-address', data)
    
    async def refund_payment(
        self,
        payment_id: Optional[str] = None,
        order_id: Optional[str] = None,
        amount: float = None,
        address: Optional[str] = None,
        network: str = None,
        is_subtract: bool = False
    ) -> Dict[str, Any]:
        """
        ????
        
        Args:
            payment_id: ??ID
            order_id: ??ID
            amount: ????
            address: ????
            network: ??
            is_subtract: ????????????
            
        Returns:
            ????
        """
        if not payment_id and not order_id:
            raise ValueError("Either payment_id or order_id must be provided")
        if not address:
            raise ValueError("Refund address must be provided")

        data = {
            'address': address,
            'is_subtract': is_subtract
        }
        
        if payment_id:
            data['uuid'] = payment_id
        if order_id:
            data['order_id'] = order_id
        if amount:
            data['amount'] = str(amount)
        if network:
            data['network'] = network
        
        return await self._make_request('POST', 'payment/refund', data)
    
    async def resend_webhook(self, payment_id: str) -> Dict[str, Any]:
        """
        ????webhook
        
        Args:
            payment_id: ??ID
            
        Returns:
            ????
        """
        data = {'uuid': payment_id}
        root_url = self._get_api_root()
        return await self._make_request('POST', f"{root_url}/v2/payment/resend", data)
    
    async def test_webhook(self, payment_id: str) -> Dict[str, Any]:
        """
        ??webhook
        
        Args:
            payment_id: ??ID
            
        Returns:
            ????
        """
        data = {'uuid': payment_id}
        return await self._make_request('POST', 'test-webhook/payment', data)

    def _get_api_root(self) -> str:
        base_url = self.base_url.rstrip('/')
        if base_url.endswith('/v1') or base_url.endswith('/v2'):
            return base_url.rsplit('/', 1)[0]
        return base_url

    def _build_webhook_body(self, payload: Dict[str, Any]) -> bytes:
        payload_data = dict(payload)
        payload_data.pop('sign', None)
        json_str = json.dumps(payload_data, separators=(',', ':'), ensure_ascii=False)
        json_str = json_str.replace("/", "\\/")
        return json_str.encode('utf-8')
    
    def verify_webhook_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Verify webhook signature from body payload and payment API key.
        """
        try:
            if not signature:
                return False
            if not isinstance(payload, dict):
                logger.error("Webhook payload must be a dict")
                return False
            key = settings.CRYPTOMUS_API_KEY
            if not key:
                logger.error("CRYPTOMUS_API_KEY missing, cannot verify webhook")
                return False
            raw_body = self._build_webhook_body(payload)
            expected_signature = self._generate_signature(raw_body, key)
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False


# ???????
def get_cryptomus_client() -> CryptomusClient:
    """??Cryptomus?????"""
    return CryptomusClient()


# ????
async def create_cryptomus_payment(
    amount: float,
    currency: str = "USD",
    order_id: str = None,
    **kwargs
) -> Dict[str, Any]:
    """???????Cryptomus??"""
    async with get_cryptomus_client() as client:
        return await client.create_payment(amount, currency, order_id, **kwargs)


async def get_cryptomus_payment_info(payment_id: str = None, order_id: str = None) -> Dict[str, Any]:
    """???????Cryptomus????"""
    async with get_cryptomus_client() as client:
        return await client.get_payment_info(payment_id, order_id)


async def get_cryptomus_balance() -> Dict[str, Any]:
    """???????Cryptomus??"""
    async with get_cryptomus_client() as client:
        return await client.get_balance()
