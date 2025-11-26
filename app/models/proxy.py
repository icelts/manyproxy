from sqlalchemy import Column, Integer, String, DateTime, Boolean, DECIMAL, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProxyProduct(Base):
    __tablename__ = "proxy_products"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(20), nullable=False, index=True)  # static, dynamic, mobile
    subcategory = Column(String(50), index=True)  # home, vn_datacenter, us_datacenter
    provider = Column(String(50), nullable=False, index=True)  # Viettel, FPT, VNPT, etc.
    product_name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(DECIMAL(10, 2), nullable=False)
    duration_days = Column(Integer, nullable=False)  # 管理员设置的固定时长
    stock = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    orders = relationship("ProxyOrder", back_populates="product")


class ProxyOrder(Base):
    __tablename__ = "proxy_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("proxy_products.id"), nullable=False, index=True)
    order_id = Column(String(100), unique=True, index=True)  # 订单号
    upstream_id = Column(String(100))  # 上游API返回的ID
    proxy_info = Column(JSON)  # 代理详细信息
    status = Column(String(20), default='active')  # active, expired, suspended
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    # 关系
    user = relationship("User", back_populates="proxy_orders")
    product = relationship("ProxyProduct", back_populates="orders")


class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False, index=True)
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time = Column(Integer)  # 响应时间（毫秒）
    ip_address = Column(String(45))  # 客户端IP
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UpstreamProvider(Base):
    __tablename__ = "upstream_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # 提供商名称
    display_name = Column(String(100), nullable=False)  # 显示名称
    api_type = Column(String(20), nullable=False)  # static, dynamic, mobile
    base_url = Column(String(200), nullable=False)  # API基础URL
    api_key_param = Column(String(50))  # API密钥参数名
    api_key_value = Column(String(200))  # API密钥值
    config = Column(JSON)  # 其他配置参数
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    product_mappings = relationship("ProductMapping", back_populates="provider")


class ProductMapping(Base):
    __tablename__ = "product_mappings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("proxy_products.id"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("upstream_providers.id"), nullable=False, index=True)
    upstream_product_code = Column(String(100), nullable=False)  # 上游产品代码
    upstream_params = Column(JSON)  # 上游API参数
    price_multiplier = Column(DECIMAL(5, 3), default=1.000)  # 价格倍数
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    product = relationship("ProxyProduct")
    provider = relationship("UpstreamProvider", back_populates="product_mappings")
