from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, func, update, and_
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
        products = result.scalars().all()
        
        return products

    @staticmethod
    async def _prepare_purchase(
        db: AsyncSession,
        user_id: int,
        product_id: Optional[int],
        category: str,
        quantity: int,
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

        actual_duration = product.duration_days or 0
        if actual_duration < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product duration is not configured"
            )

        total_price = ProxyService._calculate_total_price(product, quantity)
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
        await ProxyService._expire_user_orders(db, user_id)

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

        if proxy_order and prefix and order_id and not proxy_order.order_id.startswith(prefix):
            return None

        return proxy_order

    @staticmethod
    async def _expire_user_orders(db: AsyncSession, user_id: int) -> None:
        """自动将已过期的订单标记为 expired，避免继续出现在活跃列表。"""
        now = datetime.utcnow()
        expire_stmt = (
            update(ProxyOrder)
            .where(
                ProxyOrder.user_id == user_id,
                ProxyOrder.status == "active",
                ProxyOrder.expires_at.isnot(None),
                ProxyOrder.expires_at <= now,
            )
            .values(status="expired")
        )

        result = await db.execute(expire_stmt)
        rows = result.rowcount or 0
        if rows:
            await db.flush()
            logger.info(
                "Marked %d proxy orders as expired for user %s",
                rows,
                user_id,
            )

    @staticmethod
    def _calculate_total_price(
        product: ProxyProduct,
        quantity: int,
    ) -> Decimal:
        qty = Decimal(quantity)
        unit_price = Decimal(product.price or 0)
        raw_total = unit_price * qty
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
        )

        allow_any_provider = (product.provider or "").lower() in {"generic", "all", "*"}
        selected_provider = purchase_data.provider or product.provider
        if purchase_data.provider and not allow_any_provider and purchase_data.provider != product.provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product provider mismatch"
            )
        if allow_any_provider and not purchase_data.provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provider must be specified for this product"
            )

        # 不再限制固定时长，使用产品设置的时长

        try:
            upstream_result = await StaticProxyService.buy_proxy(
                provider=selected_provider,
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
        
        # 处理上游API响应（可能是列表或字典）
        if isinstance(upstream_result, list) and len(upstream_result) > 0:
            proxy_data = upstream_result[0]  # 取第一个元素作为代理数据
            upstream_id = str(proxy_data.get("idproxy"))
        else:
            proxy_data = upstream_result
            upstream_id = str(upstream_result.get("idproxy")) if upstream_result else None
        
        return await ProxyService._finalize_purchase(
            db,
            user=user,
            product=product,
            quantity=purchase_data.quantity,
            total_price=total_price,
            order_identifier=order_id,
            proxy_info=proxy_data,
            upstream_id=upstream_id,
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
        
        # 处理动态代理密钥获取
        upstream_id = upstream_result.get("keyxoay")
        
        # 如果没有keyxoay字段，尝试其他方式获取密钥
        if not upstream_id:
            logger.warning("响应中没有keyxoay字段，尝试获取密钥信息")
            
            # 方法1: 检查是否有其他可能的密钥字段
            possible_key_fields = ["key", "token", "access_key", "api_key", "rotation_key"]
            for field in possible_key_fields:
                if field in upstream_result:
                    upstream_id = upstream_result[field]
                    logger.info(f"从字段 {field} 获取到密钥: {upstream_id}")
                    break
            
            # 方法2: 如果仍然没有密钥，尝试调用获取密钥列表API
            if not upstream_id:
                try:
                    logger.info("尝试从上游API获取密钥列表")
                    keys_response = await DynamicProxyService.get_rotation_keys()
                    
                    if keys_response.get("status") == 100:
                        # 查找最新的密钥
                        keys_data = keys_response.get("data", [])
                        if keys_data:
                            # 取第一个或最新的密钥
                            latest_key = keys_data[0] if isinstance(keys_data, list) else keys_data
                            upstream_id = latest_key.get("keyxoay") or latest_key.get("key")
                            logger.info(f"从密钥列表获取到密钥: {upstream_id}")
                    
                except Exception as e:
                    logger.error(f"获取密钥列表失败: {e}")
            
            # 方法3: 如果还是没有，使用订单ID作为临时标识
            if not upstream_id:
                upstream_id = order_id
                logger.warning(f"无法获取密钥，使用订单ID作为临时标识: {upstream_id}")
        
        return await ProxyService._finalize_purchase(
            db,
            user=user,
            product=product,
            quantity=purchase_data.quantity,
            total_price=total_price,
            order_identifier=order_id,
            proxy_info=upstream_result,
            upstream_id=upstream_id,
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
        )

        # 根据产品ID映射到正确的Package ID
        package_id_mapping = {
            # ID 11: DynamicMobile 1day -> Package ID 2 (一天不限流量)
            11: "2",
            # ID 9: Dynamic Mobile 30days -> Package ID 13 (一个月不限流量)  
            9: "13"
        }
        
        # 获取对应的Package ID，如果没有映射则使用传入的package_id
        mapped_package_id = package_id_mapping.get(purchase_data.product_id, purchase_data.package_id)
        
        if not mapped_package_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid mobile proxy product - no Package ID mapping found"
            )

        try:
            upstream_result = await MobileProxyService.buy_proxy(
                package_id=mapped_package_id
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
        """获取用户代理列表（仅返回未过期的活跃订单）"""
        now = datetime.utcnow()
        await ProxyService._expire_user_orders(db, user_id)
        filters = [
            ProxyOrder.user_id == user_id,
            ProxyOrder.status == "active",
            or_(
                ProxyOrder.expires_at.is_(None),
                ProxyOrder.expires_at > now
            )
        ]

        # 根据类别过滤
        if category:
            if category == "static":
                filters.append(ProxyOrder.order_id.like("STATIC_%"))
            elif category == "dynamic":
                filters.append(ProxyOrder.order_id.like("DYNAMIC_%"))
            elif category == "mobile":
                filters.append(ProxyOrder.order_id.like("MOBILE_%"))

        # 构造分页查询
        offset = (page - 1) * size
        query = (
            select(ProxyOrder)
            .where(*filters)
            .order_by(ProxyOrder.created_at.desc())
            .offset(offset)
            .limit(size)
        )

        result = await db.execute(query)
        proxies = result.scalars().all()

        # 获取总数
        count_query = select(func.count()).where(*filters)
        count_result = await db.execute(count_query)
        total = count_result.scalar_one()
        
        return ProxyListResponse(
            proxies=[ProxyOrderResponse.from_orm(proxy) for proxy in proxies],
            total=total,
            page=page,
            size=size
        )
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
    async def renew_dynamic_proxy(db: AsyncSession, user_id: int, order_id: str, days: int) -> Dict[str, Any]:
        """续费动态代理"""
        await ProxyService._expire_user_orders(db, user_id)
        
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
        
        # 获取产品信息来确定原套餐时长
        product_result = await db.execute(
            select(ProxyProduct).where(ProxyProduct.id == proxy_order.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # 获取动态代理密钥
        if not proxy_order.upstream_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No proxy key found for renewal"
            )
        
        # 调用上游API续费
        try:
            upstream_result = await DynamicProxyService.renew_rotation_key(
                key=proxy_order.upstream_id,
                duration_days=days
            )
        except Exception as e:
            logger.error(f"Failed to renew dynamic proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to renew proxy from upstream"
            )
        
        # 检查上游API响应状态
        if upstream_result.get("status") != 100:
            error_msg = upstream_result.get("comen", "Unknown error")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upstream API error: {error_msg}"
            )
        
        # 更新到期时间
        new_expires_at = datetime.utcnow() + timedelta(days=days)
        proxy_order.expires_at = new_expires_at
        
        # 更新代理信息
        if proxy_order.proxy_info and isinstance(proxy_order.proxy_info, dict):
            proxy_order.proxy_info.update({
                "renewal_status": upstream_result.get("status"),
                "renewal_message": upstream_result.get("comen"),
                "last_renewed": datetime.utcnow().isoformat()
            })
        else:
            proxy_order.proxy_info = upstream_result
        
        await db.commit()
        
        return {
            "upstream_result": upstream_result,
            "new_expires_at": new_expires_at.isoformat(),
            "order_id": order_id,
            "renewal_days": days
        }

    @staticmethod
    async def renew_dynamic_proxy_auto(db: AsyncSession, user_id: int,
                                      order_id: Optional[str] = None,
                                      token: Optional[str] = None) -> Dict[str, Any]:
        """自动续费动态代理（按原套餐时长）"""
        await ProxyService._expire_user_orders(db, user_id)

        if not order_id and not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="order_id or token is required"
            )

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
        
        # 获取产品信息来确定原套餐时长
        product_result = await db.execute(
            select(ProxyProduct).where(ProxyProduct.id == proxy_order.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # 获取原套餐时长
        duration_days = product.duration_days
        if not duration_days or duration_days < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product duration is not configured"
            )
        
        # 计算续费费用
        total_price = ProxyService._calculate_total_price(product, 1)
        
        # 检查用户余额
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        current_balance = Decimal(user.balance or 0)
        if current_balance < total_price:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")
        
        # 扣除余额
        balance_before = current_balance
        new_balance = ProxyService._quantize(balance_before - total_price)
        user.balance = new_balance
        
        # 创建交易记录
        now = datetime.utcnow()
        description = f"Renew {product.product_name} for {duration_days} days"
        
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
            type="renewal",
            amount=total_price,
            balance_before=balance_before,
            balance_after=new_balance,
            description=description,
        )
        db.add(transaction)

        balance_log = BalanceLog(
            user_id=user.id,
            type="renewal",
            amount=total_price,
            balance_before=balance_before,
            balance_after=new_balance,
            description=description,
            related_order_id=order.id,
        )
        db.add(balance_log)
        
        # 调用原有的续费方法
        upstream_result = await ProxyService.renew_dynamic_proxy(
            db, user_id, proxy_order.order_id, duration_days
        )

        return {
            "upstream_result": upstream_result,
            "renewal_info": {
                "duration_days": duration_days,
                "amount": total_price,
                "new_balance": new_balance,
                "description": description
            }
        }
    
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
    async def renew_mobile_proxy(db: AsyncSession, user_id: int, order_id: str, days: int) -> Dict[str, Any]:
        """续费移动代理"""
        await ProxyService._expire_user_orders(db, user_id)
        
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
        
        # 获取移动代理密钥
        if not proxy_order.upstream_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No proxy key found for renewal"
            )
        
        # 调用上游API续费
        try:
            upstream_result = await MobileProxyService.extend_key(
                key_code=proxy_order.upstream_id
            )
        except Exception as e:
            logger.error(f"Failed to renew mobile proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to renew proxy from upstream"
            )
        
        # 检查上游API响应状态
        if upstream_result.get("status") != 1:
            error_msg = upstream_result.get("message", "Unknown error")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upstream API error: {error_msg}"
            )
        
        # 更新到期时间
        if "data" in upstream_result and "expired_time" in upstream_result["data"]:
            new_expires_at = datetime.fromisoformat(
                upstream_result["data"]["expired_time"].replace("Z", "+00:00")
            )
            proxy_order.expires_at = new_expires_at
        
        # 更新代理信息
        if "data" in upstream_result:
            proxy_order.proxy_info = upstream_result["data"]
        else:
            # 如果没有data字段，更新现有代理信息
            if proxy_order.proxy_info and isinstance(proxy_order.proxy_info, dict):
                proxy_order.proxy_info.update({
                    "renewal_status": upstream_result.get("status"),
                    "renewal_message": upstream_result.get("message"),
                    "last_renewed": datetime.utcnow().isoformat()
                })
            else:
                proxy_order.proxy_info = upstream_result
        
        await db.commit()
        
        return {
            "upstream_result": upstream_result,
            "new_expires_at": proxy_order.expires_at.isoformat() if proxy_order.expires_at else None,
            "order_id": order_id,
            "renewal_days": days
        }

    @staticmethod
    async def renew_mobile_proxy_auto(db: AsyncSession, user_id: int,
                                     order_id: Optional[str] = None,
                                     token: Optional[str] = None) -> Dict[str, Any]:
        """自动续费移动代理（按原套餐时长）"""
        await ProxyService._expire_user_orders(db, user_id)

        if not order_id and not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="order_id or token is required"
            )

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
        
        # 获取产品信息来确定原套餐时长
        product_result = await db.execute(
            select(ProxyProduct).where(ProxyProduct.id == proxy_order.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # 获取原套餐时长
        duration_days = product.duration_days
        if not duration_days or duration_days < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product duration is not configured"
            )
        
        # 计算续费费用
        total_price = ProxyService._calculate_total_price(product, 1)
        
        # 检查用户余额
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        current_balance = Decimal(user.balance or 0)
        if current_balance < total_price:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")
        
        # 扣除余额
        balance_before = current_balance
        new_balance = ProxyService._quantize(balance_before - total_price)
        user.balance = new_balance
        
        # 创建交易记录
        now = datetime.utcnow()
        description = f"Renew {product.product_name} for {duration_days} days"
        
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
            type="renewal",
            amount=total_price,
            balance_before=balance_before,
            balance_after=new_balance,
            description=description,
        )
        db.add(transaction)

        balance_log = BalanceLog(
            user_id=user.id,
            type="renewal",
            amount=total_price,
            balance_before=balance_before,
            balance_after=new_balance,
            description=description,
            related_order_id=order.id,
        )
        db.add(balance_log)
        
        # 调用原有的续费方法
        upstream_result = await ProxyService.renew_mobile_proxy(
            db, user_id, proxy_order.order_id, duration_days
        )

        return {
            "upstream_result": upstream_result,
            "renewal_info": {
                "duration_days": duration_days,
                "amount": total_price,
                "new_balance": new_balance,
                "description": description
            }
        }

    @staticmethod
    async def get_proxy_stats(db: AsyncSession, user_id: int) -> ProxyStatsResponse:
        """获取代理统计信息"""
        await ProxyService._expire_user_orders(db, user_id)
        base_query = select(ProxyOrder).where(ProxyOrder.user_id == user_id)
        result = await db.execute(base_query)
        orders = result.scalars().all()

        now = datetime.utcnow()
        active_filters = [
            ProxyOrder.user_id == user_id,
            ProxyOrder.status == "active",
            or_(
                ProxyOrder.expires_at.is_(None),
                ProxyOrder.expires_at > now
            )
        ]
        active_result = await db.execute(
            select(ProxyOrder).where(*active_filters)
        )
        active_orders = active_result.scalars().all()

        expired_filters = [
            ProxyOrder.user_id == user_id,
            or_(
                ProxyOrder.status == "expired",
                and_(
                    ProxyOrder.expires_at.isnot(None),
                    ProxyOrder.expires_at <= now
                )
            )
        ]
        expired_result = await db.execute(
            select(func.count()).where(*expired_filters)
        )
        expired_proxies = expired_result.scalar_one() or 0

        total_proxies = len(orders)
        active_proxies = len(active_orders)

        by_category = {"static": 0, "dynamic": 0, "mobile": 0}
        by_provider = {}

        for order in active_orders:
            if order.order_id.startswith("STATIC_"):
                by_category["static"] += 1
                # 尝试从多个可能的字段获取provider信息
                proxy_info = order.proxy_info or {}
                provider = (
                    proxy_info.get("loaiproxy") or 
                    proxy_info.get("provider") or 
                    proxy_info.get("type") or 
                    "unknown"
                )
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
        await ProxyService._expire_user_orders(db, user_id)
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
        
        # 获取产品信息来确定当前代理类型
        product_result = await db.execute(
            select(ProxyProduct).where(ProxyProduct.id == proxy_order.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # 从产品信息获取当前代理类型
        current_provider = product.provider
        if not current_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot determine current proxy type from product"
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
        await ProxyService._expire_user_orders(db, user_id)
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
        
        # 获取产品信息来确定代理类型
        product_result = await db.execute(
            select(ProxyProduct).where(ProxyProduct.id == proxy_order.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # 从产品信息获取代理类型
        provider = product.provider
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot determine proxy type from product"
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
        await ProxyService._expire_user_orders(db, user_id)
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
        
        # 获取产品信息来确定代理类型
        product_result = await db.execute(
            select(ProxyProduct).where(ProxyProduct.id == proxy_order.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # 从产品信息获取代理类型
        provider = product.provider
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot determine proxy type from product"
            )
        
        # 调用上游API续费
        try:
            # 处理upstream_id，确保它是整数
            proxy_id = proxy_order.upstream_id
            if isinstance(proxy_id, str):
                # 如果是字符串，尝试提取数字部分
                import re
                numbers = re.findall(r'\d+', proxy_id)
                if numbers:
                    proxy_id = int(numbers[0])
                else:
                    # 如果没有数字，使用默认值1
                    proxy_id = 1
            else:
                proxy_id = int(proxy_id)
            
            upstream_result = await StaticProxyService.renew_proxy(
                provider=provider,
                proxy_id=proxy_id,
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
        
        # 更新到期时间，但保留原有的完整代理信息
        new_time = upstream_result.get("time")
        if new_time:
            proxy_order.expires_at = datetime.fromtimestamp(new_time)
        
        # 保留原有的完整代理信息，只更新状态相关字段
        if proxy_order.proxy_info and isinstance(proxy_order.proxy_info, dict):
            # 只更新状态和时间相关字段，保留连接信息
            proxy_order.proxy_info.update({
                "status": upstream_result.get("status", proxy_order.proxy_info.get("status")),
                "time": upstream_result.get("time", proxy_order.proxy_info.get("time"))
            })
        else:
            # 如果没有原有信息，则使用续费响应
            proxy_order.proxy_info = upstream_result
        
        await db.commit()
        
        return upstream_result

    @staticmethod
    async def renew_static_proxy_auto(db: AsyncSession, user_id: int, order_id: str) -> Dict[str, Any]:
        """自动续费静态代理（按原套餐时长）"""
        await ProxyService._expire_user_orders(db, user_id)
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
        
        # 获取产品信息来确定代理类型和原套餐时长
        product_result = await db.execute(
            select(ProxyProduct).where(ProxyProduct.id == proxy_order.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # 获取原套餐时长
        duration_days = product.duration_days
        if not duration_days or duration_days < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product duration is not configured"
            )
        
        # 计算续费费用
        total_price = ProxyService._calculate_total_price(product, 1)
        
        # 检查用户余额
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        current_balance = Decimal(user.balance or 0)
        if current_balance < total_price:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")
        
        # 扣除余额
        balance_before = current_balance
        new_balance = ProxyService._quantize(balance_before - total_price)
        user.balance = new_balance
        
        # 创建交易记录
        now = datetime.utcnow()
        description = f"Renew {product.product_name} for {duration_days} days"
        
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
            type="renewal",
            amount=total_price,
            balance_before=balance_before,
            balance_after=new_balance,
            description=description,
        )
        db.add(transaction)

        balance_log = BalanceLog(
            user_id=user.id,
            type="renewal",
            amount=total_price,
            balance_before=balance_before,
            balance_after=new_balance,
            description=description,
            related_order_id=order.id,
        )
        db.add(balance_log)
        
        # 调用原有的续费方法
        upstream_result = await ProxyService.renew_static_proxy(db, user_id, order_id, duration_days)
        
        return {
            "upstream_result": upstream_result,
            "renewal_info": {
                "duration_days": duration_days,
                "amount": total_price,
                "new_balance": new_balance,
                "description": description
            }
        }

    @staticmethod
    async def export_static_proxies(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """导出所有静态代理为txt格式"""
        await ProxyService._expire_user_orders(db, user_id)
        # 获取用户的所有静态代理
        result = await db.execute(
            select(ProxyOrder).where(
                ProxyOrder.user_id == user_id,
                ProxyOrder.order_id.like("STATIC_%"),
                ProxyOrder.status == "active"
            )
        )
        static_proxies = result.scalars().all()
        
        if not static_proxies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active static proxies found"
            )
        
        # 格式化为txt格式
        proxy_lines = []
        for proxy_order in static_proxies:
            info = proxy_order.proxy_info or {}
            auth_info = info.get("auth", {})
            
            ip = info.get("ip") or info.get("proxy") or info.get("proxyhttp") or info.get("proxy_http")
            port = info.get("port") or info.get("port_proxy") or info.get("porthttp") or info.get("port_http")
            username = info.get("user") or info.get("username") or auth_info.get("user")
            password = info.get("password") or info.get("pass") or auth_info.get("pass")
            
            if ip and port and username and password:
                proxy_lines.append(f"{ip}:{port}:{username}:{password}")
        
        if not proxy_lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid proxy information found"
            )
        
        return {
            "format": "txt",
            "content": "\n".join(proxy_lines),
            "count": len(proxy_lines),
            "filename": f"static_proxies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        }

    @staticmethod
    async def export_dynamic_proxies(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """导出所有动态代理的key"""
        await ProxyService._expire_user_orders(db, user_id)
        # 获取用户的所有动态代理
        result = await db.execute(
            select(ProxyOrder).where(
                ProxyOrder.user_id == user_id,
                ProxyOrder.order_id.like("DYNAMIC_%"),
                ProxyOrder.status == "active"
            )
        )
        dynamic_proxies = result.scalars().all()
        
        if not dynamic_proxies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active dynamic proxies found"
            )
        
        # 提取所有key
        keys = []
        for proxy_order in dynamic_proxies:
            if proxy_order.upstream_id:
                keys.append(proxy_order.upstream_id)
        
        if not keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid dynamic proxy keys found"
            )
        
        return {
            "format": "txt",
            "content": "\n".join(keys),
            "count": len(keys),
            "filename": f"dynamic_keys_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        }
    
    @staticmethod
    async def get_upstream_proxy_list(db: AsyncSession, user_id: int, provider: str, 
                                    proxy_id: Optional[str] = None) -> Dict[str, Any]:
        """获取上游代理列表"""
        await ProxyService._expire_user_orders(db, user_id)
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
