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
from app.services.cryptomus_client import get_cryptomus_client
from app.models.order import OrderType, OrderStatus, PaymentMethod, CryptoCurrency
from app.models.user import User
from app.api.v1.endpoints.session import get_current_active_user
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"], include_in_schema=False)


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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """用户充值"""
    if recharge_data.method == PaymentMethod.CRYPTO:
        if not recharge_data.crypto_currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="crypto_currency is required for crypto payments"
            )
        # 如果前端未传网络，使用允许列表的第一个作为默认
        if not recharge_data.crypto_network:
            try:
                default_network = next(iter(crypto_payment_service.allowed_networks))
            except StopIteration:
                default_network = None
            if not default_network:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="crypto_network is required for crypto payments"
                )
            recharge_data.crypto_network = default_network
    try:
        base_url = settings.FRONTEND_BASE_URL or str(request.base_url).rstrip('/')
        success_url = f"{base_url}/frontend/pages/recharge.html" if base_url else None
        return await OrderService.recharge_balance(
            db,
            current_user.id,
            recharge_data.amount,
            recharge_data.method,
            recharge_data.crypto_currency,
            recharge_data.crypto_network,
            success_url=success_url
        )
    except RuntimeError as e:
        # 常见：未配置Cryptomus等支付环境
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Recharge failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


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
    
    await crypto_payment_service.update_payment_status(
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


@router.post("/payments/cryptomus-webhook")
async def cryptomus_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Cryptomus Webhook回调接口"""
    try:
        # 获取请求数据
        body = await request.body()
        webhook_data = json.loads(body.decode('utf-8'))
        
        # 获取Cryptomus签名
        signature = webhook_data.get("sign")
        if not signature:
            logger.warning("Cryptomus webhook missing signature")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing signature"
            )
        
        # 验证签名
        if not crypto_payment_service.verify_webhook_signature(webhook_data, signature):
            logger.warning("Invalid Cryptomus webhook signature")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid signature"
            )
        
        # 获取支付信息
        payment_uuid = webhook_data.get('uuid')
        order_id = webhook_data.get('order_id')
        payment_status = webhook_data.get('status') or webhook_data.get('payment_status', 'check')
        transaction_hash = webhook_data.get('txid')
        confirmations = webhook_data.get('confirmations', 0)
        required_confirmations = webhook_data.get('required_confirmations') or webhook_data.get('confirmations_required')
        
        if not payment_uuid and not order_id:
            logger.error("Cryptomus webhook missing payment identifiers")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing payment identifiers"
            )

        resolved_payment_id = order_id
        if not resolved_payment_id and payment_uuid:
            try:
                async with get_cryptomus_client() as client:
                    info = await client.get_payment_info(payment_id=payment_uuid)
                resolved_payment_id = (info.get('result') or {}).get('order_id')
            except Exception as lookup_error:
                logger.warning(
                    "Failed to resolve Cryptomus order_id for uuid %s: %s",
                    payment_uuid,
                    lookup_error,
                )
        if not resolved_payment_id:
            resolved_payment_id = payment_uuid
        if not resolved_payment_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing payment identifier")

        # 从DB获取支付记录（强一致校验）
        payment_record = await OrderService.get_payment_by_id(db, resolved_payment_id)
        if not payment_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        confirmations = crypto_payment_service._parse_int(confirmations)
        if confirmations is None:
            confirmations = 0
        required_confirmations = crypto_payment_service._parse_int(required_confirmations)
        if required_confirmations is None:
            required_confirmations = payment_record.required_confirmations

        # 基础校验：订单/商户/金额/币种
        stored_payment = await crypto_payment_service.get_cached_payment(resolved_payment_id)
        if order_id and payment_record.order_id and order_id != (stored_payment or {}).get('order_id', order_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order id mismatch")
        if settings.CRYPTOMUS_MERCHANT_UUID and webhook_data.get('merchant') and webhook_data.get('merchant') != settings.CRYPTOMUS_MERCHANT_UUID:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid merchant")

        incoming_amount = webhook_data.get('order_amount') or webhook_data.get('amount')
        if incoming_amount is not None:
            try:
                from decimal import Decimal
                if Decimal(str(payment_record.amount)) != Decimal(str(incoming_amount)):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount mismatch")
            except Exception:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount parse error")

        incoming_currency = webhook_data.get('currency')
        if incoming_currency and payment_record.crypto_currency and str(incoming_currency).upper() != payment_record.crypto_currency.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Currency mismatch")
        
        # 转换状态
        converted_status = crypto_payment_service._convert_cryptomus_status(payment_status)

        if converted_status in ['confirmed', 'paid'] and required_confirmations and confirmations < required_confirmations:
            confirmations = required_confirmations

        # 如果已经是终态且重复通知，直接返回成功（幂等）
        if stored_payment and crypto_payment_service._is_final_status(stored_payment.get('status', '')) and crypto_payment_service._is_final_status(converted_status) and converted_status == stored_payment.get('status'):
            return {"status": "success", "detail": "duplicate webhook"}
        
        # 更新支付状态
        await crypto_payment_service.update_payment_status(
            payment_id=resolved_payment_id,
            status=converted_status,
            transaction_hash=transaction_hash,
            confirmations=confirmations,
            required_confirmations=required_confirmations
        )
        
        # 如果支付已确认，处理订单
        if converted_status in ['confirmed', 'paid']:
            success = await OrderService.confirm_payment(
                db,
                resolved_payment_id,
                transaction_hash,
                confirmations,
                required_confirmations=required_confirmations
            )

            if success:
                logger.info(f"Cryptomus payment confirmed: {resolved_payment_id}")
            else:
                logger.error(f"Failed to confirm Cryptomus payment: {resolved_payment_id}")

        logger.info(f"Cryptomus webhook processed: {resolved_payment_id} - {payment_status}")
        return {"status": "success"}
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in Cryptomus webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON"
        )
    except Exception as e:
        logger.error(f"Error processing Cryptomus webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


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
    payment_status = await crypto_payment_service.get_payment_status(payment_id)

    status_value = (payment_status.get('status') or '').lower()
    if status_value in ['confirmed', 'paid']:
        confirmations = crypto_payment_service._parse_int(payment_status.get('confirmations'))
        required_confirmations = crypto_payment_service._parse_int(payment_status.get('required_confirmations'))
        if required_confirmations is None:
            required_confirmations = payment.required_confirmations
        if confirmations is None or (required_confirmations and confirmations < required_confirmations):
            confirmations = required_confirmations or confirmations or 0
            payment_status['confirmations'] = confirmations
            payment_status['required_confirmations'] = required_confirmations
        transaction_hash = payment_status.get('transaction_hash') or payment_status.get('txid') or ''
        await OrderService.confirm_payment(
            db,
            payment_id,
            transaction_hash,
            confirmations or 0,
            required_confirmations=required_confirmations
        )
    
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
    crypto_status = await crypto_payment_service.get_payment_status(payment_id)
    
    return {
        "payment": payment_response,
        "crypto_status": crypto_status
    }


@router.get("/crypto/currencies")
async def get_supported_currencies():
    """获取支持的加密货币列表"""
    return await crypto_payment_service.get_supported_currencies()


@router.post("/crypto/rates/update")
async def update_exchange_rates():
    """更新汇率"""
    updated_rates = crypto_payment_service.update_exchange_rates()
    return {"message": "Exchange rates updated", "rates": updated_rates}


@router.get("/crypto/balance")
async def get_crypto_balance():
    """获取Cryptomus账户余额"""
    try:
        if not settings.CRYPTOMUS_API_KEY or not settings.CRYPTOMUS_MERCHANT_UUID:
            return {"error": "Cryptomus not configured"}
        
        async with get_cryptomus_client() as client:
            balance = await client.get_balance()
            return balance
    except Exception as e:
        logger.error(f"Failed to get Cryptomus balance: {str(e)}")
        return {"error": str(e)}
