from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, desc, func
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import secrets

from app.models.order import Order, Payment, Transaction, BalanceLog, OrderType, OrderStatus, PaymentMethod, CryptoCurrency
from app.models.user import User
from app.schemas.order import (
    OrderCreate, OrderResponse, OrderList, PaymentCreate, PaymentResponse,
    TransactionCreate, TransactionResponse, BalanceLogCreate, BalanceLogResponse,
    RechargeRequest, RechargeResponse, OrderStats, PaymentStats, FinanceStats
)
from app.services.crypto_payment import crypto_payment_service


class OrderService:
    @staticmethod
    async def generate_order_number() -> str:
        """生成订单号"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = secrets.token_hex(4).upper()
        return f"ORD{timestamp}{random_str}"

    @staticmethod
    async def generate_payment_id() -> str:
        """生成支付ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = secrets.token_hex(6).upper()
        return f"PAY{timestamp}{random_str}"

    @staticmethod
    async def generate_transaction_id() -> str:
        """生成交易ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = secrets.token_hex(6).upper()
        return f"TXN{timestamp}{random_str}"

    @staticmethod
    async def create_order(db: AsyncSession, user_id: int, order_data: OrderCreate) -> OrderResponse:
        """创建订单"""
        order_number = await OrderService.generate_order_number()
        
        order = Order(
            order_number=order_number,
            user_id=user_id,
            type=order_data.type,
            amount=order_data.amount,
            description=order_data.description,
            status=OrderStatus.PENDING
        )
        
        db.add(order)
        await db.commit()
        await db.refresh(order)
        
        return OrderResponse.from_orm(order)

    @staticmethod
    async def get_user_orders(
        db: AsyncSession, 
        user_id: int, 
        page: int = 1, 
        size: int = 20,
        status: Optional[OrderStatus] = None,
        order_type: Optional[OrderType] = None
    ) -> OrderList:
        """获取用户订单列表"""
        query = select(Order).where(Order.user_id == user_id)
        
        if status:
            query = query.where(Order.status == status)
        if order_type:
            query = query.where(Order.type == order_type)
        
        # 获取总数
        count_query = select(func.count(Order.id)).where(Order.user_id == user_id)
        if status:
            count_query = count_query.where(Order.status == status)
        if order_type:
            count_query = count_query.where(Order.type == order_type)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        query = query.order_by(desc(Order.created_at)).offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        orders = result.scalars().all()
        
        return OrderList(
            orders=[OrderResponse.from_orm(order) for order in orders],
            total=total,
            page=page,
            size=size
        )

    @staticmethod
    async def get_order_by_id(db: AsyncSession, order_id: int, user_id: Optional[int] = None) -> Optional[Order]:
        """根据ID获取订单"""
        query = select(Order).where(Order.id == order_id)
        if user_id:
            query = query.where(Order.user_id == user_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_order_status(db: AsyncSession, order_id: int, status: OrderStatus) -> Optional[Order]:
        """更新订单状态"""
        result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if order:
            order.status = status
            order.updated_at = datetime.utcnow()
            
            if status == OrderStatus.PAID:
                order.paid_at = datetime.utcnow()
            elif status == OrderStatus.COMPLETED:
                order.completed_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(order)
        
        return order

    @staticmethod
    async def create_payment(
        db: AsyncSession, 
        user_id: int, 
        payment_data: PaymentCreate,
        crypto_amount: Optional[Decimal] = None,
        wallet_address: Optional[str] = None,
        expires_minutes: int = 30,
        required_confirmations: Optional[int] = None,
        payment_id_override: Optional[str] = None
    ) -> PaymentResponse:
        """创建支付记录"""
        payment_id = payment_id_override or await OrderService.generate_payment_id()
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
        confirmations_required = required_confirmations
        if confirmations_required is None:
            confirmations_required = 1 if payment_data.crypto_currency == CryptoCurrency.USDT else 2
        
        payment = Payment(
            payment_id=payment_id,
            order_id=payment_data.order_id,
            user_id=user_id,
            method=payment_data.method,
            amount=payment_data.amount,
            crypto_currency=payment_data.crypto_currency,
            crypto_amount=crypto_amount,
            wallet_address=wallet_address,
            expires_at=expires_at,
            required_confirmations=confirmations_required
        )
        
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        
        return PaymentResponse.from_orm(payment)

    @staticmethod
    async def get_payment_by_id(db: AsyncSession, payment_id: str) -> Optional[Payment]:
        """根据支付ID获取支付记录"""
        result = await db.execute(
            select(Payment).where(Payment.payment_id == payment_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_payment_status(
        db: AsyncSession, 
        payment_id: str, 
        status: str,
        transaction_hash: Optional[str] = None,
        confirmations: Optional[int] = None
    ) -> Optional[Payment]:
        """更新支付状态"""
        result = await db.execute(
            select(Payment).where(Payment.payment_id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if payment:
            payment.status = status
            if transaction_hash:
                payment.transaction_hash = transaction_hash
            if confirmations is not None:
                payment.confirmations = confirmations
            if status == "confirmed":
                payment.confirmed_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(payment)
        
        return payment

    @staticmethod
    async def create_transaction(
        db: AsyncSession,
        user_id: int,
        transaction_data: TransactionCreate
    ) -> TransactionResponse:
        """创建交易记录"""
        transaction_id = await OrderService.generate_transaction_id()
        
        transaction = Transaction(
            transaction_id=transaction_id,
            order_id=transaction_data.order_id,
            user_id=user_id,
            type=transaction_data.type,
            amount=transaction_data.amount,
            balance_before=transaction_data.balance_before,
            balance_after=transaction_data.balance_after,
            description=transaction_data.description
        )
        
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        
        return TransactionResponse.from_orm(transaction)

    @staticmethod
    async def create_balance_log(
        db: AsyncSession,
        user_id: int,
        log_data: BalanceLogCreate,
        admin_id: Optional[int] = None
    ) -> BalanceLogResponse:
        """创建余额变动日志"""
        balance_log = BalanceLog(
            user_id=user_id,
            type=log_data.type,
            amount=log_data.amount,
            balance_before=log_data.balance_before,
            balance_after=log_data.balance_after,
            description=log_data.description,
            related_order_id=log_data.related_order_id,
            admin_id=admin_id
        )
        
        db.add(balance_log)
        await db.commit()
        await db.refresh(balance_log)
        
        return BalanceLogResponse.from_orm(balance_log)

    @staticmethod
    async def get_user_balance_logs(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        size: int = 20
    ) -> List[BalanceLogResponse]:
        """获取用户余额变动日志"""
        query = select(BalanceLog).where(BalanceLog.user_id == user_id)\
            .order_by(desc(BalanceLog.created_at))\
            .offset((page - 1) * size).limit(size)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        return [BalanceLogResponse.from_orm(log) for log in logs]

    @staticmethod
    async def recharge_balance(
        db: AsyncSession,
        user_id: int,
        amount: Decimal,
        payment_method: PaymentMethod,
        crypto_currency: Optional[CryptoCurrency] = None,
        crypto_network: Optional[str] = None
    ) -> RechargeResponse:
        """用户充值"""
        # 创建充值订单
        order_data = OrderCreate(
            type=OrderType.RECHARGE,
            amount=amount,
            description=f"余额充值 - {payment_method.value}"
        )
        order = await OrderService.create_order(db, user_id, order_data)
        
        # 如果是加密货币支付，使用支付服务
        if payment_method == PaymentMethod.CRYPTO and crypto_currency:
            if not crypto_network:
                raise ValueError("crypto_network is required for crypto payments")
            # 预先生成支付ID，确保链路一致
            payment_identifier = await OrderService.generate_payment_id()
            crypto_payment = await crypto_payment_service.create_payment(
                float(amount),
                crypto_currency.value,
                payment_id=payment_identifier,
                network=crypto_network
            )
            
            payment_data = PaymentCreate(
                order_id=order.id,
                method=payment_method,
                amount=amount,
                crypto_currency=crypto_currency
            )
            
            payment = await OrderService.create_payment(
                db=db,
                user_id=user_id,
                payment_data=payment_data,
                crypto_amount=Decimal(crypto_payment['crypto_amount']),
                wallet_address=crypto_payment['wallet_address'],
                required_confirmations=crypto_payment.get('required_confirmations'),
                payment_id_override=payment_identifier
            )
            
            # 优先使用 Cryptomus 返回的二维码数据，缺省再本地生成
            qr_code = crypto_payment.get('address_qr_code') or crypto_payment_service.generate_qr_code(
                crypto_payment['payment_id'],
                crypto_payment['wallet_address'],
                crypto_payment['crypto_amount'],
                crypto_payment['crypto_currency']
            )
            
            return RechargeResponse(
                order=order,
                payment=payment,
                qr_code=qr_code,
                crypto_payment=crypto_payment
            )
        else:
            # 其他支付方式的处理
            payment_data = PaymentCreate(
                order_id=order.id,
                method=payment_method,
                amount=amount,
                crypto_currency=crypto_currency
            )
            
            payment = await OrderService.create_payment(
                db, user_id, payment_data
            )
            
            return RechargeResponse(
                order=order,
                payment=payment,
                qr_code=None
            )

    @staticmethod
    async def confirm_payment(
        db: AsyncSession,
        payment_id: str,
        transaction_hash: str,
        confirmations: int
    ) -> bool:
        """确认支付"""
        async with db.begin():
            payment_result = await db.execute(
                select(Payment).where(Payment.payment_id == payment_id).with_for_update()
            )
            payment = payment_result.scalar_one_or_none()
            if not payment:
                return False

            # 检查确认数是否足够
            status = "confirmed" if confirmations >= payment.required_confirmations else "pending"
            await crypto_payment_service.update_payment_status(
                payment_id=payment_id,
                status=status,
                transaction_hash=transaction_hash,
                confirmations=confirmations
            )

            payment.status = status
            payment.transaction_hash = transaction_hash or payment.transaction_hash
            payment.confirmations = confirmations
            if status == "confirmed" and not payment.confirmed_at:
                payment.confirmed_at = datetime.utcnow()

            if status != "confirmed":
                return False

            order_result = await db.execute(
                select(Order).where(Order.id == payment.order_id).with_for_update()
            )
            order = order_result.scalar_one_or_none()
            if not order:
                return False

            already_credited = bool(order.credited_at) or order.status == OrderStatus.COMPLETED
            if order.type == OrderType.RECHARGE and not already_credited:
                existing_log = await db.execute(
                    select(BalanceLog.id)
                    .where(
                        BalanceLog.related_order_id == order.id,
                        BalanceLog.type == "recharge"
                    )
                    .limit(1)
                )
                if existing_log.scalar_one_or_none():
                    already_credited = True

                existing_txn = await db.execute(
                    select(Transaction.id)
                    .where(
                        Transaction.order_id == order.id,
                        Transaction.type == "recharge"
                    )
                    .limit(1)
                )
                if existing_txn.scalar_one_or_none():
                    already_credited = True

            if already_credited:
                if order.type == OrderType.RECHARGE and not order.credited_at:
                    order.credited_at = order.completed_at or datetime.utcnow()
                if order.status == OrderStatus.PENDING:
                    order.status = OrderStatus.PAID
                    if not order.paid_at:
                        order.paid_at = datetime.utcnow()
                if order.type == OrderType.RECHARGE and order.status != OrderStatus.COMPLETED:
                    order.status = OrderStatus.COMPLETED
                    if not order.completed_at:
                        order.completed_at = datetime.utcnow()
                return True

            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.PAID
                order.paid_at = datetime.utcnow()
            elif order.status == OrderStatus.PAID and not order.paid_at:
                order.paid_at = datetime.utcnow()

            # 如果是充值订单，增加用户余额
            if order.type == OrderType.RECHARGE:
                user_result = await db.execute(
                    select(User).where(User.id == payment.user_id).with_for_update()
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    return False

                balance_before = Decimal(user.balance or 0)
                balance_after = balance_before + Decimal(order.amount)
                user.balance = balance_after

                credited_time = datetime.utcnow()

                transaction = Transaction(
                    transaction_id=await OrderService.generate_transaction_id(),
                    order_id=order.id,
                    user_id=payment.user_id,
                    type="recharge",
                    amount=order.amount,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    description="充值到账"
                )
                db.add(transaction)

                balance_log = BalanceLog(
                    user_id=payment.user_id,
                    type="recharge",
                    amount=order.amount,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    description="充值到账",
                    related_order_id=order.id
                )
                db.add(balance_log)

                order.status = OrderStatus.COMPLETED
                order.completed_at = credited_time
                order.credited_at = credited_time

        return True

    @staticmethod
    async def get_order_stats(db: AsyncSession) -> OrderStats:
        """获取订单统计"""
        # 总订单数和金额
        total_result = await db.execute(
            select(
                func.count(Order.id).label('total_orders'),
                func.sum(Order.amount).label('total_amount')
            ).where(Order.type == OrderType.PURCHASE)
        )
        total_data = total_result.first()
        
        # 各状态订单数
        status_result = await db.execute(
            select(
                Order.status,
                func.count(Order.id).label('count')
            ).where(Order.type == OrderType.PURCHASE)
            .group_by(Order.status)
        )
        status_data = {row.status: row.count for row in status_result}
        
        return OrderStats(
            total_orders=total_data.total_orders or 0,
            total_amount=total_data.total_amount or Decimal('0'),
            pending_orders=status_data.get(OrderStatus.PENDING, 0),
            paid_orders=status_data.get(OrderStatus.PAID, 0),
            completed_orders=status_data.get(OrderStatus.COMPLETED, 0),
            cancelled_orders=status_data.get(OrderStatus.CANCELLED, 0)
        )

    @staticmethod
    async def get_payment_stats(db: AsyncSession) -> PaymentStats:
        """获取支付统计"""
        try:
            # 总支付数和金额
            total_count_result = await db.execute(select(func.count(Payment.id)))
            total_payments = total_count_result.scalar() or 0
            
            total_amount_result = await db.execute(select(func.sum(Payment.amount)))
            total_amount = total_amount_result.scalar() or Decimal('0')
            
            # 加密货币支付统计
            crypto_count_result = await db.execute(
                select(func.count(Payment.id)).where(Payment.method == PaymentMethod.CRYPTO)
            )
            crypto_payments = crypto_count_result.scalar() or 0
            
            crypto_amount_result = await db.execute(
                select(func.sum(Payment.crypto_amount)).where(Payment.method == PaymentMethod.CRYPTO)
            )
            crypto_amount = crypto_amount_result.scalar() or Decimal('0')
            
            # 成功率 - 分别查询总数和成功数
            success_count_result = await db.execute(
                select(func.count(Payment.id)).where(Payment.status == 'confirmed')
            )
            success_count = success_count_result.scalar() or 0
            
            success_rate = (success_count / total_payments * 100) if total_payments > 0 else 0
            
            return PaymentStats(
                total_payments=total_payments,
                total_amount=total_amount,
                crypto_payments=crypto_payments,
                crypto_amount=crypto_amount,
                success_rate=success_rate
            )
        except Exception as e:
            # 如果查询失败，返回默认值
            return PaymentStats(
                total_payments=0,
                total_amount=Decimal('0'),
                crypto_payments=0,
                crypto_amount=Decimal('0'),
                success_rate=0.0
            )
