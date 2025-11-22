from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from decimal import Decimal

from app.core.config import settings
from app.core.database import get_db
from app.schemas.order import (
    OrderResponse, OrderList, PaymentResponse, TransactionResponse,
    BalanceLogResponse, RechargeRequest, RechargeResponse, PaymentCallback
)
from app.services.order_service import OrderService
from app.services.crypto_payment import crypto_payment_service
from app.models.order import OrderType, OrderStatus, PaymentMethod, CryptoCurrency
from app.models.user import User
from app.api.v1.endpoints.session import get_current_active_user

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=OrderList)
async def get_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    order_type: Optional[OrderType] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取用户订单列表"""
    return await OrderService.get_user_orders(
        db, current_user.id, page, size, status, order_type
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取订单详情"""
    order = await OrderService.get_order_by_id(db, order_id, current_user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return OrderResponse.from_orm(order)


@router.post("/recharge", response_model=RechargeResponse)
async def recharge_balance(
    recharge_data: RechargeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """用户充值"""
    if recharge_data.method == PaymentMethod.CRYPTO and not recharge_data.crypto_currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="crypto_currency is required for crypto payments"
        )
    
    return await OrderService.recharge_balance(
        db, current_user.id, recharge_data.amount, recharge_data.method, recharge_data.crypto_currency
    )


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取支付详情"""
    payment = await OrderService.get_payment_by_id(db, payment_id)
    if not payment or payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    return PaymentResponse.from_orm(payment)


@router.post("/payments/callback")
async def payment_callback(
    callback_data: PaymentCallback,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """支付回调接口"""
    token = request.headers.get("X-Callback-Token")
    if not token or token != settings.PAYMENT_CALLBACK_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid callback token"
        )
    
    crypto_payment_service.update_payment_status(
        payment_id=callback_data.payment_id,
        status=callback_data.status,
        transaction_hash=callback_data.transaction_hash,
        confirmations=callback_data.confirmations
    )
    
    success = await OrderService.confirm_payment(
        db, callback_data.payment_id, callback_data.transaction_hash, callback_data.confirmations
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment confirmation failed"
        )
    
    return {"message": "Payment confirmed successfully"}


@router.get("/balance/logs", response_model=list[BalanceLogResponse])
async def get_balance_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取余额变动日志"""
    return await OrderService.get_user_balance_logs(db, current_user.id, page, size)


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取交易详情"""
    from sqlalchemy.future import select
    from app.models.order import Transaction
    
    result = await db.execute(
        select(Transaction).where(
            Transaction.transaction_id == transaction_id,
            Transaction.user_id == current_user.id
        )
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return TransactionResponse.from_orm(transaction)


@router.get("/payments/{payment_id}/monitor")
async def monitor_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """监控支付状态"""
    # 检查支付是否属于当前用户
    payment = await OrderService.get_payment_by_id(db, payment_id)
    if not payment or payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # 获取支付状态
    payment_status = crypto_payment_service.get_payment_status(payment_id)
    
    return payment_status


@router.get("/payments/{payment_id}/qrcode")
async def get_payment_qrcode(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取支付二维码"""
    # 检查支付是否属于当前用户
    payment = await OrderService.get_payment_by_id(db, payment_id)
    if not payment or payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # 生成二维码
    if payment.wallet_address and payment.crypto_amount and payment.crypto_currency:
        qr_code = crypto_payment_service.generate_qr_code(
            payment_id,
            payment.wallet_address,
            str(payment.crypto_amount),
            payment.crypto_currency.value
        )
        return {"qr_code": qr_code}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment does not support QR code"
        )


@router.post("/payments/{payment_id}/verify")
async def verify_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """验证支付状态"""
    # 检查支付是否属于当前用户
    payment = await OrderService.get_payment_by_id(db, payment_id)
    if not payment or payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    payment_response = PaymentResponse.from_orm(payment)
    crypto_status = crypto_payment_service.get_payment_status(payment_id)
    
    return {
        "payment": payment_response,
        "crypto_status": crypto_status
    }


@router.get("/crypto/currencies")
async def get_supported_currencies():
    """获取支持的加密货币列表"""
    return crypto_payment_service.get_supported_currencies()


@router.post("/crypto/rates/update")
async def update_exchange_rates():
    """更新汇率"""
    updated_rates = crypto_payment_service.update_exchange_rates()
    return {"message": "Exchange rates updated", "rates": updated_rates}
