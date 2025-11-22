from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProxyProductBase(BaseModel):
    category: str
    subcategory: Optional[str] = None
    provider: str
    product_name: str
    description: Optional[str] = None
    price: float
    duration_days: int = 30
    stock: int = 0


class ProxyProductCreate(ProxyProductBase):
    pass


class ProxyProductUpdate(BaseModel):
    product_name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None


class ProxyProductResponse(ProxyProductBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProxyOrderBase(BaseModel):
    product_id: int


class ProxyOrderCreate(ProxyOrderBase):
    quantity: int = 1
    protocol: str = "HTTP"  # HTTP, SOCKS5
    username: Optional[str] = "random"
    password: Optional[str] = "random"


class StaticProxyPurchase(ProxyOrderCreate):
    provider: str  # Viettel, FPT, VNPT, US, DatacenterA, etc.
    duration_days: int = 30


class DynamicProxyPurchase(BaseModel):
    product_id: int
    duration_days: int = 30
    quantity: int = 1


class MobileProxyPurchase(BaseModel):
    product_id: int
    package_id: str
    quantity: int = 1


class ProxyOrderResponse(BaseModel):
    id: int
    order_id: str
    product_id: int
    upstream_id: Optional[str] = None
    proxy_info: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProxyInfo(BaseModel):
    ip: str
    port: int
    username: str
    password: str
    type: str
    proxy: str  # 完整代理字符串


class StaticProxyInfo(ProxyInfo):
    provider: str
    idproxy: int


class DynamicProxyInfo(BaseModel):
    proxyhttp: str
    proxysocks5: str
    nha_mang: str
    vi_tri: str
    token_expiration_date: str


class MobileProxyInfo(BaseModel):
    key_code: str
    user: str
    server: str
    server_port: int
    proxy: str
    status: int
    total_download: int
    total_upload: int
    expired_time: str
    bandwidth_limit: int


class ProxyListResponse(BaseModel):
    proxies: List[ProxyOrderResponse]
    total: int
    page: int
    size: int


class ProxyStatsResponse(BaseModel):
    total_proxies: int
    active_proxies: int
    expired_proxies: int
    by_category: Dict[str, int]
    by_provider: Dict[str, int]


class APIUsageResponse(BaseModel):
    id: int
    endpoint: str
    method: str
    status_code: int
    response_time: Optional[int] = None
    ip_address: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIUsageStats(BaseModel):
    total_requests: int
    success_requests: int
    error_requests: int
    avg_response_time: float
    requests_by_endpoint: Dict[str, int]
    requests_by_hour: Dict[str, int]


# 上游提供商相关Schema
class UpstreamProviderBase(BaseModel):
    name: str
    display_name: str
    api_type: str
    base_url: str
    api_key_param: Optional[str] = None
    api_key_value: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class UpstreamProviderCreate(UpstreamProviderBase):
    pass


class UpstreamProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key_param: Optional[str] = None
    api_key_value: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class UpstreamProviderResponse(UpstreamProviderBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# 产品映射相关Schema
class ProductMappingBase(BaseModel):
    product_id: int
    provider_id: int
    upstream_product_code: str
    upstream_params: Optional[Dict[str, Any]] = None
    price_multiplier: float = 1.000


class ProductMappingCreate(ProductMappingBase):
    pass


class ProductMappingUpdate(BaseModel):
    upstream_product_code: Optional[str] = None
    upstream_params: Optional[Dict[str, Any]] = None
    price_multiplier: Optional[float] = None
    is_active: Optional[bool] = None


class ProductMappingResponse(ProductMappingBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # 包含关联信息
    product: Optional[ProxyProductResponse] = None
    provider: Optional[UpstreamProviderResponse] = None
    
    class Config:
        from_attributes = True


# 增强的产品响应Schema
class ProxyProductResponseEnhanced(ProxyProductResponse):
    mappings: Optional[List[ProductMappingResponse]] = None
    
    class Config:
        from_attributes = True
