import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class UpstreamAPIService:
    """上游API服务基类"""
    
    @staticmethod
    async def _make_request(method: str, url: str, **kwargs) -> Dict[str, Any]:
        """发送HTTP请求"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise


class StaticProxyService(UpstreamAPIService):
    """静态代理服务 - 基于topproxy.vn API"""
    
    BASE_URL = "https://topproxy.vn/apiv2"
    API_KEY = settings.TOPPROXY_KEY
    
    # 支持的代理类型
    SUPPORTED_PROVIDERS = [
        "Viettel", "FPT", "VNPT", "US", 
        "DatacenterA", "DatacenterB", "DatacenterC",
        "GoiViettel", "GoiVNPT", "GoiDATACENTER"
    ]
    
    @classmethod
    async def buy_proxy(cls, provider: str, quantity: int, days: int, 
                       protocol: str, username: str = "random", 
                       password: str = "random") -> Dict[str, Any]:
        """
        购买静态代理
        
        Args:
            provider: 代理类型 (Viettel, FPT, VNPT, US, DatacenterA, DatacenterB, DatacenterC, GoiViettel, GoiVNPT, GoiDATACENTER)
            quantity: 购买数量
            days: 购买天数
            protocol: HTTP 或 SOCKS5
            username: 代理用户名 (默认为 random)
            password: 代理密码 (默认为 random)
        
        Returns:
            API响应结果
        """
        url = f"{cls.BASE_URL}/muaproxy.php"
        params = {
            "key": cls.API_KEY,
            "loaiproxy": provider,
            "soluong": quantity,
            "ngay": days,
            "type": protocol,
            "user": username,
            "password": password
        }
        
        return await cls._make_request("GET", url, params=params)
    
    @classmethod
    async def change_proxy(cls, provider: str, target_provider: str, proxy_id: int,
                          protocol: str, username: str = "random", 
                          password: str = "random") -> Dict[str, Any]:
        """
        更换代理类型
        
        Args:
            provider: 原代理类型
            target_provider: 目标代理类型
            proxy_id: 代理ID
            protocol: HTTP 或 SOCKS5
            username: 代理用户名
            password: 代理密码
        
        Returns:
            API响应结果
        """
        url = f"{cls.BASE_URL}/doiproxy.php"
        params = {
            "key": cls.API_KEY,
            "loaiproxy": provider,
            "loaiproxynhan": target_provider,
            "idproxy": proxy_id,
            "type": protocol,
            "user": username,
            "password": password
        }
        
        return await cls._make_request("GET", url, params=params)
    
    @classmethod
    async def change_proxy_security(cls, provider: str, proxy_id: int, 
                                  protocol: str, username: str = "random", 
                                  password: str = "random") -> Dict[str, Any]:
        """
        更改代理安全信息
        
        Args:
            provider: 代理类型
            proxy_id: 代理ID
            protocol: HTTP 或 SOCKS5
            username: 代理用户名
            password: 代理密码
        
        Returns:
            API响应结果
        """
        url = f"{cls.BASE_URL}/doibaomat.php"
        params = {
            "key": cls.API_KEY,
            "loaiproxy": provider,
            "idproxy": proxy_id,
            "type": protocol,
            "user": username,
            "password": password
        }
        
        return await cls._make_request("GET", url, params=params)
    
    @classmethod
    async def renew_proxy(cls, provider: str, proxy_id: int, days: int) -> Dict[str, Any]:
        """
        续费代理
        
        Args:
            provider: 代理类型
            proxy_id: 代理ID
            days: 续费天数
        
        Returns:
            API响应结果
        """
        url = f"{cls.BASE_URL}/giahanproxy.php"
        params = {
            "key": cls.API_KEY,
            "loaiproxy": provider,
            "idproxy": proxy_id,
            "ngay": days
        }
        
        return await cls._make_request("GET", url, params=params)
    
    @classmethod
    async def list_proxies(cls, provider: str, proxy_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取已购买代理列表
        
        Args:
            provider: 代理类型
            proxy_id: 代理ID，如果为 "all" 则获取所有代理
        
        Returns:
            API响应结果
        """
        url = f"{cls.BASE_URL}/listproxy.php"
        params = {
            "key": cls.API_KEY,
            "loaiproxy": provider,
            "idproxy": proxy_id or "all"
        }
        
        return await cls._make_request("GET", url, params=params)
    
    @classmethod
    def check_status(cls, response: Dict[str, Any]) -> tuple[bool, str]:
        """
        检查API响应状态
        
        Args:
            response: API响应
        
        Returns:
            (是否成功, 状态消息)
        """
        status = response.get("status")
        
        if status == 100:
            return True, "操作成功"
        elif status == 101:
            return False, "API密钥不存在"
        elif status == 102:
            return False, "余额不足"
        elif status == 103:
            return False, "该代理类型已售罄"
        elif status == 104:
            return False, "未知错误"
        elif status == 201:
            return True, "购买成功但数量不足"
        else:
            return False, f"未知状态码: {status}"


class DynamicProxyService(UpstreamAPIService):
    """动态代理服务"""
    
    BASE_URL = "https://proxyxoay.shop/api"
    TOPPROXY_URL = "https://topproxy.vn/proxyxoay"
    API_KEY = settings.TOPPROXY_KEY
    
    @classmethod
    async def buy_rotation_key(cls, duration_days: int, quantity: int = 1) -> Dict[str, Any]:
        """购买轮换密钥"""
        # 根据天数选择对应的端点
        if duration_days == 1:
            url = f"{cls.TOPPROXY_URL}/apimuangay.php"
        elif duration_days == 7:
            url = f"{cls.TOPPROXY_URL}/apimuatuan.php"
        else:  # 30天或其他
            url = f"{cls.TOPPROXY_URL}/apimuathang.php"
        
        params = {
            "key": cls.API_KEY,
            "thoigian": duration_days,
            "soluong": quantity
        }
        
        return await cls._make_request("GET", url, params=params)
    
    @classmethod
    async def get_rotation_proxy(cls, key: str, carrier: str = "random", 
                               province: str = "0") -> Dict[str, Any]:
        """获取轮换代理"""
        url = f"{cls.BASE_URL}/get.php"
        params = {
            "key": key,
            "nhamang": carrier,
            "tinhthanh": province
        }
        
        return await cls._make_request("GET", url, params=params)
    
    @classmethod
    async def renew_rotation_key(cls, key: str, duration_days: int) -> Dict[str, Any]:
        """续费轮换密钥"""
        # 根据天数选择对应的端点
        if duration_days == 1:
            url = f"{cls.TOPPROXY_URL}/apigiahanngay.php"
        elif duration_days == 7:
            url = f"{cls.TOPPROXY_URL}/apigiahantuan.php"
        else:  # 30天或其他
            url = f"{cls.TOPPROXY_URL}/apigiahanthang.php"
        
        params = {
            "key": cls.API_KEY,
            "keyxoay": key,
            "thoigian": duration_days
        }
        
        return await cls._make_request("GET", url, params=params)
    
    @classmethod
    async def get_rotation_keys(cls) -> Dict[str, Any]:
        """获取所有有效的轮换密钥"""
        url = f"{cls.TOPPROXY_URL}/apigetkeyxoay.php"
        params = {"key": cls.API_KEY}
        
        return await cls._make_request("GET", url, params=params)


class MobileProxyService(UpstreamAPIService):
    """移动代理服务"""
    
    BASE_URL = "https://mproxy.vn/capi"
    TOKEN = settings.MPROXY_TOKEN
    
    @classmethod
    async def buy_proxy(cls, package_id: str) -> Dict[str, Any]:
        """购买移动代理"""
        url = f"{cls.BASE_URL}/{cls.TOKEN}/buy/{package_id}"
        
        return await cls._make_request("POST", url)
    
    @classmethod
    async def get_keys(cls) -> Dict[str, Any]:
        """获取密钥列表"""
        url = f"{cls.BASE_URL}/{cls.TOKEN}/keys"
        
        return await cls._make_request("GET", url)
    
    @classmethod
    async def reset_ip(cls, key_code: str) -> Dict[str, Any]:
        """重置IP"""
        url = f"{cls.BASE_URL}/{cls.TOKEN}/key/{key_code}/resetIp"
        
        return await cls._make_request("POST", url)
    
    @classmethod
    async def extend_key(cls, key_code: str) -> Dict[str, Any]:
        """续费密钥"""
        url = f"{cls.BASE_URL}/{cls.TOKEN}/key/{key_code}/extend"
        
        return await cls._make_request("POST", url)
