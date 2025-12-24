from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.models.order import OrderType, OrderStatus, PaymentMethod, CryptoCurrency


# Order相关Schema
class OrderBase(BaseModel):
    type: OrderType
    amount: Decimal = Field(gt=0, description="订单金额必须大于0")
    description: Optional[str] = None


class OrderCreate(OrderBase):
    pass


class OrderResponse(BaseModel):
    id: int
    order_number: str
    user_id: int
    type: OrderType
    amount: Decimal
    status: OrderStatus
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    paid_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class OrderList(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int
    size: int


# Payment相关Schema
class PaymentBase(BaseModel):
    method: PaymentMethod
    amount: Decimal = Field(gt=0, description="支付金额必须大于0")
    crypto_currency: Optional[CryptoCurrency] = None


class PaymentCreate(PaymentBase):
    order_id: int


class CryptoPaymentCreate(BaseModel):
    order_id: int
    crypto_currency: CryptoCurrency


class PaymentResponse(BaseModel):
    id: int
    payment_id: str
    order_id: int
    user_id: int
    method: PaymentMethod
    amount: Decimal
    currency: str
    status: str
    crypto_currency: Optional[CryptoCurrency]
    crypto_amount: Optional[Decimal]
    wallet_address: Optional[str]
    transaction_hash: Optional[str]
    confirmations: int
    required_confirmations: int
    expires_at: Optional[datetime]
    created_at: datetime
    confirmed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Transaction相关Schema
class TransactionBase(BaseModel):
    type: str
    amount: Decimal
    description: Optional[str] = None


class TransactionCreate(TransactionBase):
    order_id: int
    balance_before: Decimal
    balance_after: Decimal


class TransactionResponse(BaseModel):
    id: int
    transaction_id: str
    order_id: int
    user_id: int
    type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# BalanceLog相关Schema
class BalanceLogBase(BaseModel):
    type: str
    amount: Decimal
    description: Optional[str] = None


class BalanceLogCreate(BalanceLogBase):
    balance_before: Decimal
    balance_after: Decimal
    related_order_id: Optional[int] = None


class BalanceLogResponse(BaseModel):
    id: int
    user_id: int
    type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    description: Optional[str]
    related_order_id: Optional[int]
    admin_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# 充值相关Schema
class RechargeRequest(BaseModel):
    amount: Decimal = Field(gt=0, description="充值金额必须大于0")
    method: PaymentMethod = PaymentMethod.CRYPTO
    crypto_currency: Optional[CryptoCurrency] = None
    crypto_network: Optional[str] = None


class RechargeResponse(BaseModel):
    order: OrderResponse
    payment: PaymentResponse
    qr_code: Optional[str] = None  # 二维码数据
    crypto_payment: Optional[Dict[str, Any]] = None


# 支付回调Schema
class PaymentCallback(BaseModel):
    payment_id: str
    transaction_hash: str
    confirmations: int
    status: str


# 统计相关Schema
class OrderStats(BaseModel):
    total_orders: int
    total_amount: Decimal
    pending_orders: int
    paid_orders: int
    completed_orders: int
    cancelled_orders: int


class PaymentStats(BaseModel):
    total_payments: int
    total_amount: Decimal
    crypto_payments: int
    crypto_amount: Decimal
    success_rate: float


class FinanceStats(BaseModel):
    total_revenue: Decimal
    today_revenue: Decimal
    week_revenue: Decimal
    month_revenue: Decimal
    total_users: int
    active_users: int
    order_stats: OrderStats
    payment_stats: PaymentStats
