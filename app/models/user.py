from sqlalchemy import Column, Integer, String, DateTime, Boolean, DECIMAL, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    balance = Column(DECIMAL(10, 2), default=0.00)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    api_keys = relationship("APIKey", back_populates="user")
    proxy_orders = relationship("ProxyOrder", back_populates="user")
    balance_logs = relationship("BalanceLog", foreign_keys="BalanceLog.user_id", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    orders = relationship("Order", back_populates="user")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    api_key = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(100))
    rate_limit = Column(Integer, default=1000)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))

    # 关系
    user = relationship("User", back_populates="api_keys")
