from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, EmailStr


class SessionLogin(BaseModel):
    """登录请求负载。"""

    username: str
    password: str


class SessionUser(BaseModel):
    """统一的前端用户描述。"""

    id: int
    username: str
    email: EmailStr
    is_active: bool
    is_admin: bool
    balance: float

    class Config:
        from_attributes = True


class SessionPageState(BaseModel):
    """登录后单个页面的访问状态。"""

    allowed: bool
    reason: Optional[str] = None


class SessionEnvelope(BaseModel):
    """封装统一的登录/状态响应。"""

    token: str
    token_type: str
    user: SessionUser
    abilities: Dict[str, bool]
    pages: Dict[str, SessionPageState]
    refreshed_at: datetime


class SessionLogoutResponse(BaseModel):
    """登出响应。"""

    message: str = "logged out"
