from fastapi import APIRouter
from app.api.v1.endpoints import admin, orders, proxy, session

api_router = APIRouter(prefix="/api/v1")

# 对外文档仅保留指定接口，其余路由仍可用但不出现在 OpenAPI
api_router.include_router(session.router, include_in_schema=False)
api_router.include_router(orders.router, include_in_schema=False)
api_router.include_router(admin.router, include_in_schema=False)
api_router.include_router(proxy.router)
