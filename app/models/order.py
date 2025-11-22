from sqlalchemy import Column, Integer, String, DateTime, Boolean, DECIMAL, Text, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class OrderType(str, enum.Enum):
    RECHARGE = "recharge"  # 充值订单
    PURCHASE = "purchase"  # 购买订单


class OrderStatus(str, enum.Enum):
    PENDING = "pending"      # 待支付
    PAID = "paid"           # 已支付
    COMPLETED = "completed" # 已完成
    CANCELLED = "cancelled" # 已取消
    REFUNDED = "refunded"   # 已退款


class PaymentMethod(str, enum.Enum):
    CRYPTO = "crypto"  # 加密货币支付
    BANK = "bank"      # 银行转账
    ALIPAY = "alipay"  # 支付宝
    WECHAT = "wechat"  # 微信支付


class CryptoCurrency(str, enum.Enum):
    BTC = "BTC"   # 比特币
    ETH = "ETH"   # 以太坊
    USDT = "USDT" # 泰达币
    USDC = "USDC" # USD Coin


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(32), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(OrderType), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    paid_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # 关系
    user = relationship("User", back_populates="orders")
    payments = relationship("Payment", back_populates="order")
    transactions = relationship("Transaction", back_populates="order")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(64), unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    method = Column(Enum(PaymentMethod), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(String(20), default="pending")  # pending, confirmed, failed, expired
    crypto_currency = Column(Enum(CryptoCurrency))  # 加密货币类型
    crypto_amount = Column(DECIMAL(20, 8))  # 加密货币金额
    wallet_address = Column(String(255))  # 支付地址
    transaction_hash = Column(String(255))  # 区块链交易哈希
    confirmations = Column(Integer, default=0)  # 确认数
    required_confirmations = Column(Integer, default=1)  # 需要的确认数
    expires_at = Column(DateTime(timezone=True))  # 支付过期时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True))

    # 关系
    order = relationship("Order", back_populates="payments")
    user = relationship("User", back_populates="payments")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(64), unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # recharge, purchase, refund
    amount = Column(DECIMAL(10, 2), nullable=False)
    balance_before = Column(DECIMAL(10, 2), nullable=False)
    balance_after = Column(DECIMAL(10, 2), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    order = relationship("Order", back_populates="transactions")
    user = relationship("User")


class BalanceLog(Base):
    __tablename__ = "balance_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # recharge, purchase, refund, admin_adjust
    amount = Column(DECIMAL(10, 2), nullable=False)
    balance_before = Column(DECIMAL(10, 2), nullable=False)
    balance_after = Column(DECIMAL(10, 2), nullable=False)
    description = Column(Text)
    related_order_id = Column(Integer, ForeignKey("orders.id"))
    admin_id = Column(Integer, ForeignKey("users.id"))  # 管理员ID（仅管理员操作时）
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", foreign_keys=[user_id], back_populates="balance_logs")
    related_order = relationship("Order")
    admin = relationship("User", foreign_keys=[admin_id])
