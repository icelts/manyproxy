from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.proxy import (
    ProxyOrderResponse
)
from app.services.proxy_service import ProxyService
from typing import Optional

# 创建公共API路由，只包含更换IP相关的接口
public_router = APIRouter(prefix="/api/v1", tags=["IP更换服务"])


def get_current_api_user(request: Request) -> int:
    """从中间件获取当前用户ID（仅支持API Key认证）"""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled"
        )
    return getattr(user, "id", None) or getattr(request.state, "user_id", None)


@public_router.post("/mobile/{order_id}/reset", response_model=ProxyOrderResponse)
async def reset_mobile_proxy(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """重置移动代理IP - 更换新的IP地址"""
    return await ProxyService.reset_mobile_proxy(
        db,
        user_id,
        order_id=order_id
    )


@public_router.post("/mobile/token/{token}/reset", response_model=ProxyOrderResponse)
async def reset_mobile_proxy_by_token(
    token: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """通过token重置移动代理IP - 更换新的IP地址"""
    return await ProxyService.reset_mobile_proxy(
        db,
        user_id,
        token=token
    )


@public_router.get("/dynamic/{order_id}")
async def get_dynamic_proxy(
    order_id: str,
    carrier: str = Query("random", description="运营商"),
    province: str = Query("0", description="省份"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """获取动态代理 - 每次请求获取新的IP地址"""
    return await ProxyService.get_dynamic_proxy(
        db,
        user_id,
        order_id=order_id,
        carrier=carrier,
        province=province
    )


@public_router.get("/dynamic/token/{token}")
async def get_dynamic_proxy_by_token(
    token: str,
    carrier: str = Query("random", description="运营商"),
    province: str = Query("0", description="省份"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """通过上游token获取动态代理 - 每次请求获取新的IP地址"""
    return await ProxyService.get_dynamic_proxy(
        db,
        user_id,
        token=token,
        carrier=carrier,
        province=province
    )


@public_router.post("/static/{order_id}/change")
async def change_static_proxy(
    order_id: str,
    target_provider: str = Query(..., description="目标代理类型"),
    protocol: str = Query("HTTP", description="协议类型"),
    username: str = Query("random", description="用户名"),
    password: str = Query("random", description="密码"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """更换静态代理类型 - 获取新的IP地址和配置"""
    return await ProxyService.change_static_proxy(
        db, user_id, order_id, target_provider, protocol, username, password
    )


@public_router.post("/static/{order_id}/change-security")
async def change_proxy_security(
    order_id: str,
    protocol: str = Query("HTTP", description="协议类型"),
    username: str = Query("random", description="用户名"),
    password: str = Query("random", description="密码"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_api_user)
):
    """更改代理安全信息 - 更换用户名密码"""
    return await ProxyService.change_proxy_security(
        db, user_id, order_id, protocol, username, password
    )


# 添加API文档说明
@public_router.get("/info")
async def api_info():
    """API服务信息"""
    return {
        "service": "IP更换接口服务",
        "version": "1.0.0",
        "description": "提供代理IP更换服务的API接口",
        "endpoints": {
            "mobile_reset": "POST /api/v1/mobile/{order_id}/reset - 重置移动代理IP",
            "mobile_reset_token": "POST /api/v1/mobile/token/{token}/reset - 通过token重置移动代理IP",
            "dynamic_get": "GET /api/v1/dynamic/{order_id} - 获取动态代理IP",
            "dynamic_get_token": "GET /api/v1/dynamic/token/{token} - 通过token获取动态代理IP",
            "static_change": "POST /api/v1/static/{order_id}/change - 更换静态代理类型",
            "static_change_security": "POST /api/v1/static/{order_id}/change-security - 更改代理安全信息"
        },
        "authentication": "需要API Key认证，在请求头中添加 X-API-Key",
        "note": "所有接口都需要有效的API Key才能访问"
    }
