from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.proxy import ProxyProduct, ProxyOrder, APIUsage
from app.models.user import User
from app.models.order import Order, Transaction, BalanceLog, OrderType, OrderStatus
from app.schemas.proxy import (
    StaticProxyPurchase,
    DynamicProxyPurchase,
    MobileProxyPurchase,
    ProxyOrderResponse,
    ProxyListResponse,
    ProxyStatsResponse,
)
from app.services.order_service import OrderService
from app.services.upstream_api import (
    StaticProxyService,
    DynamicProxyService,
    MobileProxyService,
)
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)


class ProxyService:
    CURRENCY_PLACES = Decimal("0.01")

    @staticmethod
    async def get_products(db: AsyncSession, category: Optional[str] = None) -> List[ProxyProduct]:
        """获取产品列表"""
        query = select(ProxyProduct).where(ProxyProduct.is_active == True)
        if category:
            query = query.where(ProxyProduct.category == category)
        
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def _prepare_purchase(
        db: AsyncSession,
        user_id: int,
        product_id: Optional[int],
        category: str,
        quantity: int,
        duration_days: Optional[int] = None,
    ) -> Tuple[ProxyProduct, User, Decimal, int]:
        """校验商品/用户并计算金额"""
        if not product_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="product_id is required")
        if quantity < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be at least 1")

        result = await db.execute(select(ProxyProduct).where(ProxyProduct.id == product_id))
        product = result.scalar_one_or_none()
        if not product or not product.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")
        if product.category != category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product category mismatch")
        if product.stock is not None and product.stock < quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient product stock")

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

        base_duration = product.duration_days or 30
        actual_duration = duration_days or base_duration
        if actual_duration < 1:
            actual_duration = base_duration or 30

        total_price = ProxyService._calculate_total_price(product, quantity, actual_duration, base_duration)
        current_balance = Decimal(user.balance or 0)
        if current_balance < total_price:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")

        return product, user, total_price, actual_duration

    @staticmethod
    async def _get_active_order(
        db: AsyncSession,
        user_id: int,
        *,
        order_id: Optional[str] = None,
        token: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> Optional[ProxyOrder]:
        """Retrieve an active order by internal identifier or upstream token."""
        if not order_id and not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="order_id or token is required"
            )

        query = select(ProxyOrder).where(
            ProxyOrder.user_id == user_id,
            ProxyOrder.status == "active"
        )

        if order_id:
            query = query.where(ProxyOrder.order_id == order_id)
        if token:
            query = query.where(ProxyOrder.upstream_id == token)

        result = await db.execute(query)
        proxy_order = result.scalar_one_or_none()

        if proxy_order and prefix and not proxy_order.order_id.startswith(prefix):
            return None

        return proxy_order

    @staticmethod
    def _calculate_total_price(
        product: ProxyProduct,
        quantity: int,
        duration_days: int,
        base_duration: int,
    ) -> Decimal:
        price = Decimal(product.price or 0)
        qty = Decimal(quantity)
        duration = Decimal(duration_days)
        baseline = Decimal(base_duration or 1)
        duration_multiplier = duration / baseline if baseline else Decimal(1)
        raw_total = price * qty * duration_multiplier
        return ProxyService._quantize(raw_total)

    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        return value.quantize(ProxyService.CURRENCY_PLACES, rounding=ROUND_HALF_UP)

    @staticmethod
    async def _finalize_purchase(
        db: AsyncSession,
        *,
        user: User,
        product: ProxyProduct,
        quantity: int,
        total_price: Decimal,
        order_identifier: str,
        proxy_info: Dict[str, Any],
        upstream_id: Optional[str],
        expires_at: Optional[datetime],
    ) -> ProxyOrderResponse:
        """扣减余额/库存并生成订单、交易日志"""
        balance_before = Decimal(user.balance or 0)
        new_balance = ProxyService._quantize(balance_before - total_price)
        user.balance = new_balance

        if product.stock is not None:
            product.stock -= quantity

        now = datetime.utcnow()
        description = f"Purchase {product.product_name}"
        order = Order(
            order_number=await OrderService.generate_order_number(),
            user_id=user.id,
            type=OrderType.PURCHASE,
            amount=total_price,
            status=OrderStatus.COMPLETED,
            description=description,
            paid_at=now,
            completed_at=now,
        )
        db.add(order)
        await db.flush()

        transaction = Transaction(
            transaction_id=await OrderService.generate_transaction_id(),
            order_id=order.id,
            user_id=user.id,
            type="purchase",
            amount=total_price,
            balance_before=balance_before,
            balance_after=new_balance,
            description=description,
        )
        db.add(transaction)

        balance_log = BalanceLog(
            user_id=user.id,
            type="purchase",
            amount=total_price,
            balance_before=balance_before,
            balance_after=new_balance,
            description=description,
            related_order_id=order.id,
        )
        db.add(balance_log)

        proxy_order = ProxyOrder(
            user_id=user.id,
            product_id=product.id,
            order_id=order_identifier,
            upstream_id=upstream_id,
            proxy_info=proxy_info,
            status="active",
            expires_at=expires_at,
        )
        db.add(proxy_order)

        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        await db.refresh(proxy_order)
        return ProxyOrderResponse.from_orm(proxy_order)
    
    @staticmethod
    async def buy_static_proxy(db: AsyncSession, user_id: int, 
                             purchase_data: StaticProxyPurchase) -> ProxyOrderResponse:
        """购买静态代理"""
        product, user, total_price, actual_duration = await ProxyService._prepare_purchase(
            db,
            user_id=user_id,
            product_id=purchase_data.product_id,
            category="static",
            quantity=purchase_data.quantity,
            duration_days=purchase_data.duration_days,
        )

        if purchase_data.provider and purchase_data.provider != product.provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product provider mismatch"
            )

        try:
            upstream_result = await StaticProxyService.buy_proxy(
                provider=product.provider,
                quantity=purchase_data.quantity,
                days=actual_duration,
                protocol=purchase_data.protocol,
                username=purchase_data.username,
                password=purchase_data.password
            )
        except Exception as e:
            logger.error(f"Failed to buy static proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to purchase proxy from upstream"
            )
        
        success, message = StaticProxyService.check_status(upstream_result)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upstream API error: {message}"
            )
        
        order_id = f"STATIC_{uuid.uuid4().hex[:12].upper()}"
        expires_at = datetime.utcnow() + timedelta(days=actual_duration)
        
        return await ProxyService._finalize_purchase(
            db,
            user=user,
            product=product,
            quantity=purchase_data.quantity,
            total_price=total_price,
            order_identifier=order_id,
            proxy_info=upstream_result,
            upstream_id=str(upstream_result.get("idproxy")),
            expires_at=expires_at
        )

    @staticmethod
    async def buy_dynamic_proxy(db: AsyncSession, user_id: int,
                              purchase_data: DynamicProxyPurchase) -> ProxyOrderResponse:
        """购买动态代理"""
        product, user, total_price, actual_duration = await ProxyService._prepare_purchase(
            db,
            user_id=user_id,
            product_id=purchase_data.product_id,
            category="dynamic",
            quantity=purchase_data.quantity,
            duration_days=purchase_data.duration_days,
        )

        try:
            upstream_result = await DynamicProxyService.buy_rotation_key(
                duration_days=actual_duration,
                quantity=purchase_data.quantity
            )
        except Exception as e:
            logger.error(f"Failed to buy dynamic proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to purchase proxy from upstream"
            )
        
        if upstream_result.get("status") != 100:
            error_msg = upstream_result.get("comen", "Unknown error")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upstream API error: {error_msg}"
            )
        
        order_id = f"DYNAMIC_{uuid.uuid4().hex[:12].upper()}"
        expires_at = datetime.utcnow() + timedelta(days=actual_duration)
        
        return await ProxyService._finalize_purchase(
            db,
            user=user,
            product=product,
            quantity=purchase_data.quantity,
            total_price=total_price,
            order_identifier=order_id,
            proxy_info=upstream_result,
            upstream_id=upstream_result.get("keyxoay"),
            expires_at=expires_at
        )

    @staticmethod
    async def buy_mobile_proxy(db: AsyncSession, user_id: int,
                             purchase_data: MobileProxyPurchase) -> ProxyOrderResponse:
        """购买移动代理"""
        if purchase_data.quantity != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile proxy purchase currently supports quantity = 1"
            )

        product, user, total_price, _ = await ProxyService._prepare_purchase(
            db,
            user_id=user_id,
            product_id=purchase_data.product_id,
            category="mobile",
            quantity=purchase_data.quantity,
            duration_days=None,
        )

        try:
            upstream_result = await MobileProxyService.buy_proxy(
                package_id=purchase_data.package_id
            )
        except Exception as e:
            logger.error(f"Failed to buy mobile proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to purchase proxy from upstream"
            )
        
        if upstream_result.get("status") != 1:
            error_msg = upstream_result.get("message", "Unknown error")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upstream API error: {error_msg}"
            )
        
        order_id = f"MOBILE_{uuid.uuid4().hex[:12].upper()}"
        expires_at = datetime.fromisoformat(
            upstream_result["data"]["expired_time"].replace("Z", "+00:00")
        )
        
        return await ProxyService._finalize_purchase(
            db,
            user=user,
            product=product,
            quantity=purchase_data.quantity,
            total_price=total_price,
            order_identifier=order_id,
            proxy_info=upstream_result["data"],
            upstream_id=upstream_result["data"]["key_code"],
            expires_at=expires_at
        )

    @staticmethod
    async def get_user_proxies(db: AsyncSession, user_id: int, 
                             category: Optional[str] = None,
                             page: int = 1, size: int = 20) -> ProxyListResponse:
        """获取用户代理列表"""
        query = select(ProxyOrder).where(ProxyOrder.user_id == user_id)
        
        # 根据类别过滤
        if category:
            if category == "static":
                query = query.where(ProxyOrder.order_id.like("STATIC_%"))
            elif category == "dynamic":
                query = query.where(ProxyOrder.order_id.like("DYNAMIC_%"))
            elif category == "mobile":
                query = query.where(ProxyOrder.order_id.like("MOBILE_%"))
        
        # 分页
        offset = (page - 1) * size
        query = query.offset(offset).limit(size).order_by(ProxyOrder.created_at.desc())
        
        result = await db.execute(query)
        proxies = result.scalars().all()
        
        # 获取总数
        count_query = select(ProxyOrder).where(ProxyOrder.user_id == user_id)
        if category:
            if category == "static":
                count_query = count_query.where(ProxyOrder.order_id.like("STATIC_%"))
            elif category == "dynamic":
                count_query = count_query.where(ProxyOrder.order_id.like("DYNAMIC_%"))
            elif category == "mobile":
                count_query = count_query.where(ProxyOrder.order_id.like("MOBILE_%"))
        
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())
        
        return ProxyListResponse(
            proxies=[ProxyOrderResponse.from_orm(proxy) for proxy in proxies],
            total=total,
            page=page,
            size=size
        )
    
    @staticmethod
    async def get_dynamic_proxy(db: AsyncSession, user_id: int, 
    @staticmethod
    async def get_dynamic_proxy(db: AsyncSession, user_id: int,
                              order_id: Optional[str] = None, carrier: str = "random",
                              province: str = "0", token: Optional[str] = None) -> Dict[str, Any]:
        """获取动态代理"""
        proxy_order = await ProxyService._get_active_order(
            db,
            user_id,
            order_id=order_id,
            token=token,
            prefix="DYNAMIC_"
        )

        if not proxy_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proxy order not found or inactive"
            )

        try:
            upstream_result = await DynamicProxyService.get_rotation_proxy(
                key=proxy_order.upstream_id,
                carrier=carrier,
                province=province
            )
        except Exception as e:
            logger.error(f"Failed to get dynamic proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get proxy from upstream"
            )

        if upstream_result.get("status") != 100:
            error_msg = upstream_result.get("message", "Unknown error")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upstream API error: {error_msg}"
            )

        return upstream_result
    
    @staticmethod
    async def reset_mobile_proxy(db: AsyncSession, user_id: int,
                               order_id: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
        """重置移动代理IP"""
        proxy_order = await ProxyService._get_active_order(
            db,
            user_id,
            order_id=order_id,
            token=token,
            prefix="MOBILE_"
        )

        if not proxy_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proxy order not found or inactive"
            )

        try:
            upstream_result = await MobileProxyService.reset_ip(
                key_code=proxy_order.upstream_id
            )
        except Exception as e:
            logger.error(f"Failed to reset mobile proxy IP: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset IP from upstream"
            )

        if upstream_result.get("status") != 1:
            error_msg = upstream_result.get("message", "Unknown error")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upstream API error: {error_msg}"
            )

        proxy_order.proxy_info = upstream_result["data"]
        await db.commit()

        return upstream_result["data"]

    @staticmethod
    async def get_proxy_stats(db: AsyncSession, user_id: int) -> ProxyStatsResponse:
        """获取代理统计信息"""
        result = await db.execute(
            select(ProxyOrder).where(ProxyOrder.user_id == user_id)
        )
        orders = result.scalars().all()

        total_proxies = len(orders)
        active_proxies = len([o for o in orders if o.status == "active"])
        expired_proxies = len([o for o in orders if o.status == "expired"])

        by_category = {"static": 0, "dynamic": 0, "mobile": 0}
        by_provider = {}

        for order in orders:
            if order.order_id.startswith("STATIC_"):
                by_category["static"] += 1
                provider = (order.proxy_info or {}).get("loaiproxy", "unknown")
                by_provider[provider] = by_provider.get(provider, 0) + 1
            elif order.order_id.startswith("DYNAMIC_"):
                by_category["dynamic"] += 1
                by_provider["dynamic"] = by_provider.get("dynamic", 0) + 1
            elif order.order_id.startswith("MOBILE_"):
                by_category["mobile"] += 1
                by_provider["mobile"] = by_provider.get("mobile", 0) + 1

        return ProxyStatsResponse(
            total_proxies=total_proxies,
            active_proxies=active_proxies,
            expired_proxies=expired_proxies,
            by_category=by_category,
            by_provider=by_provider
        )
    @staticmethod
    async def record_api_usage(db: AsyncSession, user_id: int, api_key_id: int,
                             endpoint: str, method: str, status_code: int,
                             response_time: int, ip_address: str, user_agent: str):
        """记录API使用情况"""
        usage = APIUsage(
            user_id=user_id,
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(usage)
        await db.commit()
    
    @staticmethod
    async def change_static_proxy(db: AsyncSession, user_id: int, order_id: str,
                                target_provider: str, protocol: str = "HTTP",
                                username: str = "random", password: str = "random") -> Dict[str, Any]:
        """更换静态代理类型"""
        # 获取订单信息
        result = await db.execute(
            select(ProxyOrder).where(
                ProxyOrder.user_id == user_id,
                ProxyOrder.order_id == order_id,
                ProxyOrder.status == "active"
            )
        )
        proxy_order = result.scalar_one_or_none()
        
        if not proxy_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proxy order not found or inactive"
            )
        
        # 获取当前代理类型
        current_provider = proxy_order.proxy_info.get("loaiproxy")
        if not current_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot determine current proxy type"
            )
        
        # 调用上游API更换代理
        try:
            upstream_result = await StaticProxyService.change_proxy(
                provider=current_provider,
                target_provider=target_provider,
                proxy_id=int(proxy_order.upstream_id),
                protocol=protocol,
                username=username,
                password=password
            )
        except Exception as e:
            logger.error(f"Failed to change static proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change proxy from upstream"
            )
        
        # 检查上游API响应状态
        success, message = StaticProxyService.check_status(upstream_result)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upstream API error: {message}"
            )
        
        # 更新代理信息
        proxy_order.proxy_info = upstream_result
        await db.commit()
        
        return upstream_result
    
    @staticmethod
    async def change_proxy_security(db: AsyncSession, user_id: int, order_id: str,
                                  protocol: str = "HTTP", username: str = "random", 
                                  password: str = "random") -> Dict[str, Any]:
        """更改代理安全信息"""
        # 获取订单信息
        result = await db.execute(
            select(ProxyOrder).where(
                ProxyOrder.user_id == user_id,
                ProxyOrder.order_id == order_id,
                ProxyOrder.status == "active"
            )
        )
        proxy_order = result.scalar_one_or_none()
        
        if not proxy_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proxy order not found or inactive"
            )
        
        # 获取代理类型
        provider = proxy_order.proxy_info.get("loaiproxy")
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot determine proxy type"
            )
        
        # 调用上游API更改安全信息
        try:
            upstream_result = await StaticProxyService.change_proxy_security(
                provider=provider,
                proxy_id=int(proxy_order.upstream_id),
                protocol=protocol,
                username=username,
                password=password
            )
        except Exception as e:
            logger.error(f"Failed to change proxy security: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change proxy security from upstream"
            )
        
        # 检查上游API响应状态
        success, message = StaticProxyService.check_status(upstream_result)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upstream API error: {message}"
            )
        
        # 更新代理信息
        proxy_order.proxy_info = upstream_result
        await db.commit()
        
        return upstream_result
    
    @staticmethod
    async def renew_static_proxy(db: AsyncSession, user_id: int, order_id: str, days: int) -> Dict[str, Any]:
        """续费静态代理"""
        # 获取订单信息
        result = await db.execute(
            select(ProxyOrder).where(
                ProxyOrder.user_id == user_id,
                ProxyOrder.order_id == order_id,
                ProxyOrder.status == "active"
            )
        )
        proxy_order = result.scalar_one_or_none()
        
        if not proxy_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proxy order not found or inactive"
            )
        
        # 获取代理类型
        provider = proxy_order.proxy_info.get("loaiproxy")
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot determine proxy type"
            )
        
        # 调用上游API续费
        try:
            upstream_result = await StaticProxyService.renew_proxy(
                provider=provider,
                proxy_id=int(proxy_order.upstream_id),
                days=days
            )
        except Exception as e:
            logger.error(f"Failed to renew static proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to renew proxy from upstream"
            )
        
        # 检查上游API响应状态
        success, message = StaticProxyService.check_status(upstream_result)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upstream API error: {message}"
            )
        
        # 更新到期时间
        new_time = upstream_result.get("time")
        if new_time:
            proxy_order.expires_at = datetime.fromtimestamp(new_time)
        
        proxy_order.proxy_info = upstream_result
        await db.commit()
        
        return upstream_result
    
    @staticmethod
    async def get_upstream_proxy_list(db: AsyncSession, user_id: int, provider: str, 
                                    proxy_id: Optional[str] = None) -> Dict[str, Any]:
        """获取上游代理列表"""
        # 验证用户是否有该类型的代理
        result = await db.execute(
            select(ProxyOrder).where(
                ProxyOrder.user_id == user_id,
                ProxyOrder.order_id.like("STATIC_%"),
                ProxyOrder.status == "active"
            )
        )
        user_proxies = result.scalars().all()
        
        if not user_proxies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active static proxies found for this user"
            )
        
        # 调用上游API获取代理列表
        try:
            upstream_result = await StaticProxyService.list_proxies(
                provider=provider,
                proxy_id=proxy_id
            )
        except Exception as e:
            logger.error(f"Failed to get upstream proxy list: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get proxy list from upstream"
            )
        
        # 检查上游API响应状态
        success, message = StaticProxyService.check_status(upstream_result)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upstream API error: {message}"
            )
        
        return upstream_result
