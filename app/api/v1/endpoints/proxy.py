from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.proxy import (
    StaticProxyPurchase, DynamicProxyPurchase, MobileProxyPurchase,
    ProxyOrderResponse, ProxyListResponse, ProxyStatsResponse,
    ProxyProductResponse
)
from app.services.proxy_service import ProxyService
from app.services.upstream_api import StaticProxyService
from typing import Optional

router = APIRouter(prefix="/proxy", tags=["proxy"])


def get_current_api_user(request: Request) -> int:
    """从API Key中间件获取当前用户ID"""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key authentication required"
        )
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled"
        )
    return getattr(user, "id", None) or getattr(request.state, "user_id", None)


@router.get("/products", response_model=list[ProxyProductResponse])
async def get_products(
    category: Optional[str] = Query(None, description="产品类别"),
    db: AsyncSession = Depends(get_db)
):
    """获取产品列表"""
    products = await ProxyService.get_products(db, category)
    return [ProxyProductResponse.from_orm(product) for product in products]


@router.post("/static/buy", response_model=ProxyOrderResponse)
async def buy_static_proxy(
    purchase_data: StaticProxyPurchase,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """购买静态代理"""
    return await ProxyService.buy_static_proxy(db, user_id, purchase_data)


@router.post("/dynamic/buy", response_model=ProxyOrderResponse)
async def buy_dynamic_proxy(
    purchase_data: DynamicProxyPurchase,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """购买动态代理"""
    return await ProxyService.buy_dynamic_proxy(db, user_id, purchase_data)


@router.post("/mobile/buy", response_model=ProxyOrderResponse)
async def buy_mobile_proxy(
    purchase_data: MobileProxyPurchase,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """购买移动代理"""
    return await ProxyService.buy_mobile_proxy(db, user_id, purchase_data)


@router.get("/list", response_model=ProxyListResponse)
async def get_proxy_list(
    category: Optional[str] = Query(None, description="代理类别"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """获取用户代理列表"""
    return await ProxyService.get_user_proxies(db, user_id, category, page, size)


@router.get("/dynamic/{order_id}")
async def get_dynamic_proxy(
    order_id: str,
    carrier: str = Query("random", description="运营商"),
    province: str = Query("0", description="省份"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """获取动态代理"""
    return await ProxyService.get_dynamic_proxy(
        db,
        user_id,
        order_id=order_id,
        carrier=carrier,
        province=province
    )


@router.get("/dynamic/token/{token}")
async def get_dynamic_proxy_by_token(
    token: str,
    carrier: str = Query("random", description="运营商"),
    province: str = Query("0", description="省份"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """通过上游token获取动态代理"""
    return await ProxyService.get_dynamic_proxy(
        db,
        user_id,
        token=token,
        carrier=carrier,
        province=province
    )


@router.post("/mobile/{order_id}/reset")
async def reset_mobile_proxy(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user),
):
    """Reset mobile proxy IP"""
    return await ProxyService.reset_mobile_proxy(
        db,
        user_id,
        order_id=order_id
    )


@router.post("/mobile/token/{token}/reset")
async def reset_mobile_proxy_by_token(
    token: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user),
):
    """Reset mobile proxy IP via upstream token"""
    return await ProxyService.reset_mobile_proxy(
        db,
        user_id,
        token=token
    )


@router.get("/stats", response_model=ProxyStatsResponse)
async def get_proxy_stats(db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)):
    """获取代理统计信息"""
    return await ProxyService.get_proxy_stats(db, user_id)


# 新增静态代理管理端点
@router.post("/static/{order_id}/change")
async def change_static_proxy(
    order_id: str,
    target_provider: str = Query(..., description="目标代理类型"),
    protocol: str = Query("HTTP", description="协议类型"),
    username: str = Query("random", description="用户名"),
    password: str = Query("random", description="密码"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)):
    """更换静态代理类型"""
    return await ProxyService.change_static_proxy(
        db, user_id, order_id, target_provider, protocol, username, password
    )


@router.post("/static/{order_id}/change-security")
async def change_proxy_security(
    order_id: str,
    protocol: str = Query("HTTP", description="协议类型"),
    username: str = Query("random", description="用户名"),
    password: str = Query("random", description="密码"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)):
    """更改代理安全信息"""
    return await ProxyService.change_proxy_security(
        db, user_id, order_id, protocol, username, password
    )


@router.post("/static/{order_id}/renew")
async def renew_static_proxy(
    order_id: str,
    days: int = Query(..., ge=1, le=365, description="续费天数"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)):
    """续费静态代理"""
    return await ProxyService.renew_static_proxy(db, user_id, order_id, days)


@router.get("/static/upstream-list")
async def get_upstream_proxy_list(
    provider: str = Query(..., description="代理类型"),
    proxy_id: Optional[str] = Query(None, description="代理ID，为all获取所有"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)):
    """获取上游代理列表"""
    return await ProxyService.get_upstream_proxy_list(db, user_id, provider, proxy_id)


@router.get("/static/providers")
async def get_supported_providers():
    """获取支持的静态代理类型"""
    return {
        "providers": StaticProxyService.SUPPORTED_PROVIDERS,
        "description": "支持的静态代理类型列表"
    }
