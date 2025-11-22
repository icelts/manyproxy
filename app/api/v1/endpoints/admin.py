from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timedelta

from app.core.database import get_db
from app.schemas.order import (
    OrderResponse, OrderList, PaymentResponse, OrderStats, PaymentStats, FinanceStats
)
from app.schemas.proxy import (
    ProxyProductResponse, ProxyProductCreate, ProxyProductUpdate,
    UpstreamProviderResponse, UpstreamProviderCreate, UpstreamProviderUpdate,
    ProductMappingResponse, ProductMappingCreate, ProductMappingUpdate,
    ProxyProductResponseEnhanced
)
from app.models.proxy import UpstreamProvider, ProductMapping
from app.api.v1.endpoints.session import get_current_admin_user
from app.schemas.user import UserResponse
from app.services.order_service import OrderService
from app.models.user import User
from app.models.order import Order, Payment, OrderType, OrderStatus
from app.models.proxy import ProxyProduct

router = APIRouter(prefix="/admin", tags=["admin"])


# 用户管理
@router.get("/users", response_model=List[UserResponse])
async def get_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取用户列表"""
    
    query = select(User)
    
    if search:
        query = query.where(
            (User.username.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    query = query.order_by(desc(User.created_at)).offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [UserResponse.from_orm(user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取用户详情"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.put("/users/{user_id}/toggle")
async def toggle_user_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """切换用户状态"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = not user.is_active
    await db.commit()
    
    return {"message": f"User {'activated' if user.is_active else 'deactivated'} successfully"}


@router.post("/users/{user_id}/adjust-balance")
async def adjust_user_balance(
    user_id: int,
    amount: Decimal,
    description: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """调整用户余额"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    balance_before = user.balance
    balance_after = balance_before + amount
    
    user.balance = balance_after
    await db.commit()
    
    # 创建余额变动日志
    from app.schemas.order import BalanceLogCreate
    log_data = BalanceLogCreate(
        type="admin_adjust",
        amount=amount,
        balance_before=balance_before,
        balance_after=balance_after,
        description=description
    )
    await OrderService.create_balance_log(db, user_id, log_data, admin_user.id)
    
    return {
        "message": "Balance adjusted successfully",
        "balance_before": balance_before,
        "balance_after": balance_after,
        "adjustment": amount
    }


# 订单管理
@router.get("/orders", response_model=OrderList)
async def get_all_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    order_type: Optional[OrderType] = None,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取所有订单"""
    
    query = select(Order)
    
    if status:
        query = query.where(Order.status == status)
    if order_type:
        query = query.where(Order.type == order_type)
    if user_id:
        query = query.where(Order.user_id == user_id)
    
    # 获取总数
    count_query = select(func.count(Order.id))
    if status:
        count_query = count_query.where(Order.status == status)
    if order_type:
        count_query = count_query.where(Order.type == order_type)
    if user_id:
        count_query = count_query.where(Order.user_id == user_id)
    
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


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_detail(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取订单详情"""
    
    order = await OrderService.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return OrderResponse.from_orm(order)


@router.put("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    status: OrderStatus,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """更新订单状态"""
    
    order = await OrderService.update_order_status(db, order_id, status)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return {"message": "Order status updated successfully"}


# 支付管理
@router.get("/payments", response_model=List[PaymentResponse])
async def get_all_payments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    method: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取所有支付记录"""
    
    query = select(Payment)
    
    if status:
        query = query.where(Payment.status == status)
    if method:
        query = query.where(Payment.method == method)
    
    query = query.order_by(desc(Payment.created_at)).offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    payments = result.scalars().all()
    
    return [PaymentResponse.from_orm(payment) for payment in payments]


# 统计数据

async def _get_finance_statistics_data(db: AsyncSession) -> FinanceStats:
    """获取财务统计数据的核心逻辑"""
    # 获取订单和支付统计
    order_stats = await OrderService.get_order_stats(db)
    payment_stats = await OrderService.get_payment_stats(db)
    
    # 计算收入统计
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # 今日收入
    today_result = await db.execute(
        select(func.sum(Order.amount)).where(
            Order.type == OrderType.PURCHASE,
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= today_start
        )
    )
    today_revenue = today_result.scalar() or Decimal('0')
    
    # 本周收入
    week_result = await db.execute(
        select(func.sum(Order.amount)).where(
            Order.type == OrderType.PURCHASE,
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= week_start
        )
    )
    week_revenue = week_result.scalar() or Decimal('0')
    
    # 本月收入
    month_result = await db.execute(
        select(func.sum(Order.amount)).where(
            Order.type == OrderType.PURCHASE,
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= month_start
        )
    )
    month_revenue = month_result.scalar() or Decimal('0')
    
    # 总收入
    total_result = await db.execute(
        select(func.sum(Order.amount)).where(
            Order.type == OrderType.PURCHASE,
            Order.status == OrderStatus.COMPLETED
        )
    )
    total_revenue = total_result.scalar() or Decimal('0')
    
    # 用户统计
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()
    
    # 活跃用户（最近7天有活动的用户）
    active_users_result = await db.execute(
        select(func.count(func.distinct(Order.user_id))).where(
            Order.created_at >= week_start
        )
    )
    active_users = active_users_result.scalar()
    
    return FinanceStats(
        total_revenue=total_revenue,
        today_revenue=today_revenue,
        week_revenue=week_revenue,
        month_revenue=month_revenue,
        total_users=total_users,
        active_users=active_users,
        order_stats=order_stats,
        payment_stats=payment_stats
    )


@router.get("/stats/orders", response_model=OrderStats)
async def get_order_statistics(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取订单统计"""
    return await OrderService.get_order_stats(db)


@router.get("/stats/payments", response_model=PaymentStats)
async def get_payment_statistics(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取支付统计"""
    return await OrderService.get_payment_stats(db)


@router.get("/stats/finance", response_model=FinanceStats)
async def get_finance_statistics(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取财务统计"""
    return await _get_finance_statistics_data(db)


@router.get("/stats/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取仪表板统计数据"""
    
    # 基础统计
    finance_stats = await _get_finance_statistics_data(db)
    
    # 最近7天的订单趋势
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    
    daily_orders = []
    for i in range(7):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_result = await db.execute(
            select(
                func.count(Order.id).label('orders'),
                func.sum(Order.amount).label('revenue')
            ).where(
                Order.created_at >= day_start,
                Order.created_at < day_end
            )
        )
        day_data = day_result.first()
        
        if day_data and day_data.orders is not None:
            daily_orders.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "orders": day_data.orders,
                "revenue": float(day_data.revenue or 0)
            })
        else:
            daily_orders.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "orders": 0,
                "revenue": 0.0
            })
    
    return {
        "finance": finance_stats,
        "daily_orders": list(reversed(daily_orders)),
        "recent_activities": await get_recent_activities(db)
    }


async def get_recent_activities(db: AsyncSession, limit: int = 10) -> List[dict]:
    """获取最近活动"""
    # 获取最近的订单
    orders_result = await db.execute(
        select(Order, User.username).join(User)
        .order_by(desc(Order.created_at))
        .limit(limit)
    )
    
    activities = []
    for order, username in orders_result:
        activities.append({
            "type": "order",
            "message": f"用户 {username} 创建了{order.type.value}订单",
            "time": order.created_at.isoformat(),
            "icon": "fas fa-shopping-cart",
            "color": "text-primary"
        })
    
    return activities


# 代理产品管理 - 使用不同的路径前缀避免路由冲突
# 注意：具体路由必须在通用路由之前定义，以避免路由冲突

@router.get("/proxy-products/stats")
async def get_proxy_product_stats(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取代理产品统计信息"""
    
    # 总产品数
    total_result = await db.execute(select(func.count(ProxyProduct.id)))
    total_products = total_result.scalar()
    
    # 活跃产品数
    active_result = await db.execute(
        select(func.count(ProxyProduct.id)).where(ProxyProduct.is_active == True)
    )
    active_products = active_result.scalar()
    
    # 按类别统计
    category_stats_result = await db.execute(
        select(
            ProxyProduct.category,
            func.count(ProxyProduct.id).label('count'),
            func.avg(ProxyProduct.price).label('avg_price'),
            func.sum(ProxyProduct.stock).label('total_stock')
        ).group_by(ProxyProduct.category)
    )
    
    category_stats = []
    for category, count, avg_price, total_stock in category_stats_result:
        category_stats.append({
            "category": category,
            "count": count,
            "avg_price": float(avg_price or 0),
            "total_stock": total_stock or 0
        })
    
    # 按提供商统计
    provider_stats_result = await db.execute(
        select(
            ProxyProduct.provider,
            func.count(ProxyProduct.id).label('count'),
            func.avg(ProxyProduct.price).label('avg_price'),
            func.sum(ProxyProduct.stock).label('total_stock')
        ).group_by(ProxyProduct.provider)
        .order_by(func.count(ProxyProduct.id).desc())
        .limit(10)
    )
    
    provider_stats = []
    for provider, count, avg_price, total_stock in provider_stats_result:
        provider_stats.append({
            "provider": provider,
            "count": count,
            "avg_price": float(avg_price or 0),
            "total_stock": total_stock or 0
        })
    
    return {
        "total_products": total_products,
        "active_products": active_products,
        "inactive_products": total_products - active_products,
        "category_stats": category_stats,
        "provider_stats": provider_stats
    }


@router.get("/proxy-products/categories")
async def get_proxy_product_categories(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取代理产品类别列表"""
    
    # 获取所有类别
    categories_result = await db.execute(
        select(ProxyProduct.category, func.count(ProxyProduct.id).label('count'))
        .group_by(ProxyProduct.category)
        .order_by(ProxyProduct.category)
    )
    
    categories = []
    for category, count in categories_result:
        # 获取该类别的提供商
        providers_result = await db.execute(
            select(ProxyProduct.provider)
            .where(ProxyProduct.category == category)
            .distinct()
            .order_by(ProxyProduct.provider)
        )
        providers = [row[0] for row in providers_result]
        
        categories.append({
            "category": category,
            "count": count,
            "providers": providers
        })
    
    return {"categories": categories}


@router.get("/proxy-products", response_model=List[ProxyProductResponse])
async def get_proxy_products(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    provider: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取代理产品列表"""
    
    query = select(ProxyProduct)
    
    if category:
        query = query.where(ProxyProduct.category == category)
    if provider:
        query = query.where(ProxyProduct.provider == provider)
    if is_active is not None:
        query = query.where(ProxyProduct.is_active == is_active)
    
    query = query.order_by(ProxyProduct.category, ProxyProduct.provider).offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    products = result.scalars().all()
    
    return [ProxyProductResponse.from_orm(product) for product in products]


@router.post("/proxy-products", response_model=ProxyProductResponse)
async def create_proxy_product(
    product_data: ProxyProductCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """创建代理产品"""
    
    product = ProxyProduct(**product_data.dict())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    return ProxyProductResponse.from_orm(product)


@router.get("/proxy-products/{product_id}", response_model=ProxyProductResponse)
async def get_proxy_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取代理产品详情"""
    
    result = await db.execute(select(ProxyProduct).where(ProxyProduct.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proxy product not found"
        )
    
    return ProxyProductResponse.from_orm(product)


@router.put("/proxy-products/{product_id}", response_model=ProxyProductResponse)
async def update_proxy_product(
    product_id: int,
    product_data: ProxyProductUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """更新代理产品"""
    
    result = await db.execute(select(ProxyProduct).where(ProxyProduct.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proxy product not found"
        )
    
    # 更新字段
    update_data = product_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    await db.commit()
    await db.refresh(product)
    
    return ProxyProductResponse.from_orm(product)


@router.delete("/proxy-products/{product_id}")
async def delete_proxy_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """删除代理产品"""
    
    result = await db.execute(select(ProxyProduct).where(ProxyProduct.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proxy product not found"
        )
    
    await db.delete(product)
    await db.commit()
    
    return {"message": "Proxy product deleted successfully"}


@router.put("/proxy-products/{product_id}/toggle")
async def toggle_proxy_product_status(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """切换代理产品状态"""
    
    result = await db.execute(select(ProxyProduct).where(ProxyProduct.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proxy product not found"
        )
    
    product.is_active = not product.is_active
    await db.commit()
    
    return {"message": f"Proxy product {'activated' if product.is_active else 'deactivated'} successfully"}


# 上游提供商管理
@router.get("/upstream-providers", response_model=List[UpstreamProviderResponse])
async def get_upstream_providers(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    api_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取上游提供商列表"""
    
    query = select(UpstreamProvider)
    
    if api_type:
        query = query.where(UpstreamProvider.api_type == api_type)
    if is_active is not None:
        query = query.where(UpstreamProvider.is_active == is_active)
    
    query = query.order_by(UpstreamProvider.name).offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    providers = result.scalars().all()
    
    return [UpstreamProviderResponse.from_orm(provider) for provider in providers]


@router.post("/upstream-providers", response_model=UpstreamProviderResponse)
async def create_upstream_provider(
    provider_data: UpstreamProviderCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """创建上游提供商"""
    
    # 检查名称是否已存在
    existing_result = await db.execute(
        select(UpstreamProvider).where(UpstreamProvider.name == provider_data.name)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider name already exists"
        )
    
    provider = UpstreamProvider(**provider_data.dict())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    
    return UpstreamProviderResponse.from_orm(provider)


@router.get("/upstream-providers/{provider_id}", response_model=UpstreamProviderResponse)
async def get_upstream_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取上游提供商详情"""
    
    result = await db.execute(select(UpstreamProvider).where(UpstreamProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upstream provider not found"
        )
    
    return UpstreamProviderResponse.from_orm(provider)


@router.put("/upstream-providers/{provider_id}", response_model=UpstreamProviderResponse)
async def update_upstream_provider(
    provider_id: int,
    provider_data: UpstreamProviderUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """更新上游提供商"""
    
    result = await db.execute(select(UpstreamProvider).where(UpstreamProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upstream provider not found"
        )
    
    # 更新字段
    update_data = provider_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)
    
    await db.commit()
    await db.refresh(provider)
    
    return UpstreamProviderResponse.from_orm(provider)


@router.delete("/upstream-providers/{provider_id}")
async def delete_upstream_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """删除上游提供商"""
    
    result = await db.execute(select(UpstreamProvider).where(UpstreamProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upstream provider not found"
        )
    
    # 检查是否有关联的产品映射
    mappings_result = await db.execute(
        select(ProductMapping).where(ProductMapping.provider_id == provider_id)
    )
    if mappings_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete provider with existing product mappings"
        )
    
    await db.delete(provider)
    await db.commit()
    
    return {"message": "Upstream provider deleted successfully"}


@router.put("/upstream-providers/{provider_id}/toggle", response_model=UpstreamProviderResponse)
async def toggle_upstream_provider_status(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """切换上游提供商状态"""
    
    result = await db.execute(select(UpstreamProvider).where(UpstreamProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upstream provider not found"
        )
    
    provider.is_active = not provider.is_active
    await db.commit()
    await db.refresh(provider)
    
    return UpstreamProviderResponse.from_orm(provider)


# 产品映射管理
@router.get("/product-mappings", response_model=List[ProductMappingResponse])
async def get_product_mappings(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    product_id: Optional[int] = None,
    provider_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取产品映射列表"""
    
    query = select(ProductMapping).options(
        selectinload(ProductMapping.product),
        selectinload(ProductMapping.provider)
    )
    
    if product_id:
        query = query.where(ProductMapping.product_id == product_id)
    if provider_id:
        query = query.where(ProductMapping.provider_id == provider_id)
    if is_active is not None:
        query = query.where(ProductMapping.is_active == is_active)
    
    query = query.order_by(ProductMapping.created_at.desc()).offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    mappings = result.scalars().all()
    
    return [ProductMappingResponse.from_orm(mapping) for mapping in mappings]


@router.post("/product-mappings", response_model=ProductMappingResponse)
async def create_product_mapping(
    mapping_data: ProductMappingCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """创建产品映射"""
    
    # 检查产品是否存在
    product_result = await db.execute(
        select(ProxyProduct).where(ProxyProduct.id == mapping_data.product_id)
    )
    if not product_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # 检查提供商是否存在
    provider_result = await db.execute(
        select(UpstreamProvider).where(UpstreamProvider.id == mapping_data.provider_id)
    )
    if not provider_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    # 检查映射是否已存在
    existing_result = await db.execute(
        select(ProductMapping).where(
            ProductMapping.product_id == mapping_data.product_id,
            ProductMapping.provider_id == mapping_data.provider_id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product mapping already exists for this provider"
        )
    
    mapping = ProductMapping(**mapping_data.dict())
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    
    # 重新加载关联数据
    await db.refresh(mapping, ["product", "provider"])
    
    return ProductMappingResponse.from_orm(mapping)


@router.get("/product-mappings/{mapping_id}", response_model=ProductMappingResponse)
async def get_product_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取产品映射详情"""
    
    result = await db.execute(
        select(ProductMapping).options(
            selectinload(ProductMapping.product),
            selectinload(ProductMapping.provider)
        ).where(ProductMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product mapping not found"
        )
    
    return ProductMappingResponse.from_orm(mapping)


@router.put("/product-mappings/{mapping_id}", response_model=ProductMappingResponse)
async def update_product_mapping(
    mapping_id: int,
    mapping_data: ProductMappingUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """更新产品映射"""
    
    result = await db.execute(
        select(ProductMapping).options(
            selectinload(ProductMapping.product),
            selectinload(ProductMapping.provider)
        ).where(ProductMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product mapping not found"
        )
    
    # 更新字段
    update_data = mapping_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(mapping, field, value)
    
    await db.commit()
    await db.refresh(mapping)
    
    return ProductMappingResponse.from_orm(mapping)


@router.delete("/product-mappings/{mapping_id}")
async def delete_product_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """删除产品映射"""
    
    result = await db.execute(select(ProductMapping).where(ProductMapping.id == mapping_id))
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product mapping not found"
        )
    
    await db.delete(mapping)
    await db.commit()
    
    return {"message": "Product mapping deleted successfully"}


@router.put("/product-mappings/{mapping_id}/toggle", response_model=ProductMappingResponse)
async def toggle_product_mapping_status(
    mapping_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """切换产品映射状态"""
    
    result = await db.execute(
        select(ProductMapping).options(
            selectinload(ProductMapping.product),
            selectinload(ProductMapping.provider)
        ).where(ProductMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product mapping not found"
        )
    
    mapping.is_active = not mapping.is_active
    await db.commit()
    await db.refresh(mapping)
    
    return ProductMappingResponse.from_orm(mapping)


@router.get("/proxy-products/{product_id}/mappings", response_model=List[ProductMappingResponse])
async def get_product_mappings_by_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取指定产品的所有映射"""
    
    result = await db.execute(
        select(ProductMapping).options(
            selectinload(ProductMapping.product),
            selectinload(ProductMapping.provider)
        ).where(ProductMapping.product_id == product_id)
        .order_by(ProductMapping.created_at.desc())
    )
    mappings = result.scalars().all()
    
    return [ProductMappingResponse.from_orm(mapping) for mapping in mappings]
