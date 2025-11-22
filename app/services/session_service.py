from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import APIKey, User
from app.schemas.session import SessionEnvelope, SessionPageState, SessionUser
from app.schemas.user import APIKeyCreate, UserCreate
from app.utils.cache import CacheService


class SessionService:
    """统一的用户会话和鉴权服务。"""

    PAGE_RULES: Dict[str, Dict[str, Optional[str]]] = {
        "dashboard": {"reason": None},
        "proxy": {"reason": "INACTIVE_USER"},
        "products": {"reason": "INACTIVE_USER"},
        "orders": {"reason": "INACTIVE_USER"},
        "api-keys": {"reason": "INACTIVE_USER"},
        "profile": {"reason": "INACTIVE_USER"},
        "admin": {"reason": "ADMIN_ONLY"},
    }

    @staticmethod
    async def register_user(db: AsyncSession, user_data: UserCreate) -> User:
        """注册新用户。"""
        existing = await db.execute(select(User).where(User.username == user_data.username))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

        existing_email = await db.execute(select(User).where(User.email == user_data.email))
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        now = datetime.utcnow()
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            created_at=now,
            updated_at=now,
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def authenticate_credentials(
        db: AsyncSession, username: str, password: str
    ) -> Optional[User]:
        """使用用户名/密码验证用户。"""
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """根据主键获取用户。"""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """根据用户名获取用户。"""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def resolve_user_from_token(db: AsyncSession, token: str) -> Optional[User]:
        """从JWT中解析用户。"""
        payload = verify_token(token)
        if not payload:
            return None
        username = payload.get("sub")
        if not username:
            return None
        return await SessionService.get_user_by_username(db, username)

    @staticmethod
    def build_session_envelope(user: User, existing_token: Optional[str] = None) -> SessionEnvelope:
        """构建统一的会话响应。"""
        token_payload = {"sub": user.username}
        if user.is_admin:
            token_payload["is_admin"] = True
        token = existing_token or create_access_token(token_payload)

        session_user = SessionUser(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            balance=float(user.balance or 0),
        )

        pages = SessionService._build_page_states(user)
        abilities = SessionService._build_abilities(user)

        return SessionEnvelope(
            token=token,
            token_type="bearer",
            user=session_user,
            abilities=abilities,
            pages=pages,
            refreshed_at=datetime.utcnow(),
        )

    @staticmethod
    def _build_page_states(user: User) -> Dict[str, SessionPageState]:
        """根据用户信息计算各页面可访问性。"""
        states: Dict[str, SessionPageState] = {}
        for page, meta in SessionService.PAGE_RULES.items():
            if page == "admin":
                allowed = bool(user.is_admin)
            else:
                allowed = bool(user.is_active)
                if page == "dashboard":
                    allowed = True
            reason = None if allowed else meta.get("reason")
            states[page] = SessionPageState(allowed=allowed, reason=reason)
        return states

    @staticmethod
    def _build_abilities(user: User) -> Dict[str, bool]:
        """构建可选的能力映射。"""
        return {
            "can_purchase": bool(user.is_active),
            "can_use_api": bool(user.is_active),
            "can_manage_platform": bool(user.is_admin),
            "can_access_admin": bool(user.is_admin),
        }

    @staticmethod
    async def create_api_key(
        db: AsyncSession, user_id: int, api_key_data: APIKeyCreate
    ) -> APIKey:
        """创建新的API密钥。"""
        from app.core.security import generate_api_key

        safe_limit = max(1, min(api_key_data.rate_limit or settings.DEFAULT_RATE_LIMIT, settings.DEFAULT_RATE_LIMIT))
        now = datetime.utcnow()
        api_key = APIKey(
            user_id=user_id,
            api_key=generate_api_key(),
            name=api_key_data.name or "Default Key",
            rate_limit=safe_limit,
            created_at=now,
        )
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        await CacheService.set(
            f"api_key:{api_key.api_key}",
            {
                "user_id": api_key.user_id,
                "rate_limit": api_key.rate_limit,
                "is_active": api_key.is_active,
                "api_key_id": api_key.id,
            },
            ttl=3600,
        )
        return api_key

    @staticmethod
    async def get_api_key_info(db: AsyncSession, api_key: str) -> Optional[dict]:
        """获取API密钥数据信息。"""
        cached = await CacheService.get(f"api_key:{api_key}")
        if cached:
            return cached

        result = await db.execute(
            select(APIKey).where(APIKey.api_key == api_key, APIKey.is_active == True)
        )
        api_key_obj = result.scalar_one_or_none()
        if not api_key_obj:
            return None
        if api_key_obj.expires_at and api_key_obj.expires_at.timestamp() < time.time():
            return None

        info = {
            "user_id": api_key_obj.user_id,
            "rate_limit": api_key_obj.rate_limit,
            "is_active": api_key_obj.is_active,
            "api_key_id": api_key_obj.id,
        }
        await CacheService.set(f"api_key:{api_key}", info, ttl=3600)
        return info

    @staticmethod
    async def rotate_api_key(db: AsyncSession, user_id: int, api_key_id: int) -> APIKey:
        """轮换API密钥。"""
        result = await db.execute(
            select(APIKey).where(APIKey.id == api_key_id, APIKey.user_id == user_id)
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )

        await CacheService.delete(f"api_key:{api_key.api_key}")

        from app.core.security import generate_api_key

        api_key.api_key = generate_api_key()
        await db.commit()
        await db.refresh(api_key)

        await CacheService.set(
            f"api_key:{api_key.api_key}",
            {
                "user_id": api_key.user_id,
                "rate_limit": api_key.rate_limit,
                "is_active": api_key.is_active,
                "api_key_id": api_key.id,
            },
            ttl=3600,
        )
        return api_key
