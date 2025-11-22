from fastapi import APIRouter
from app.api.v1.endpoints import admin, orders, proxy, session

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(session.router)
api_router.include_router(proxy.router)
api_router.include_router(orders.router)
api_router.include_router(admin.router)
