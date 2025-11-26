from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password
from app.models.user import APIKey, User
from app.schemas.session import SessionEnvelope, SessionLogin, SessionLogoutResponse
from app.schemas.user import APIKeyCreate, APIKeyResponse, PasswordChange, UserCreate
from app.services.session_service import SessionService
from app.utils.cache import CacheService

router = APIRouter(prefix="/session", tags=["session"])
security = HTTPBearer()


async def get_current_active_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """公共依赖：解析并验证当前用户。"""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await SessionService.resolve_user_from_token(db, credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """管理员权限依赖。"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


@router.post("/register", response_model=SessionEnvelope)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """注册并立即返回会话状态。"""
    user = await SessionService.register_user(db, user_data)
    return await SessionService.build_session_envelope(user, db=db)


@router.post("/login", response_model=SessionEnvelope)
async def login(login_data: SessionLogin, db: AsyncSession = Depends(get_db)):
    """登录并返回统一会话状态。"""
    user = await SessionService.authenticate_credentials(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await SessionService.build_session_envelope(user, db=db)


@router.get("/state", response_model=SessionEnvelope)
async def session_state(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """获取当前用户的统一会话状态。"""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await SessionService.resolve_user_from_token(db, credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    
    return await SessionService.build_session_envelope(user, existing_token=credentials.credentials, db=db)


@router.post("/logout", response_model=SessionLogoutResponse)
async def logout():
    """前端丢弃本地状态即可，这里仅返回统一响应。"""
    return SessionLogoutResponse()


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建API密钥。"""
    api_key = await SessionService.create_api_key(db, current_user.id, api_key_data)
    return APIKeyResponse.from_orm(api_key)


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """列出当前用户的API密钥。"""
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id, APIKey.is_active == True)
    )
    api_keys = result.scalars().all()
    return [APIKeyResponse.from_orm(key) for key in api_keys]


@router.put("/api-keys/{key_id}")
async def rotate_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """轮换指定API密钥。"""
    api_key = await SessionService.rotate_api_key(db, current_user.id, key_id)
    return {"api_key": api_key.api_key, "message": "API key rotated successfully"}


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除API密钥。"""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    api_key.is_active = False
    await db.commit()
    await CacheService.delete(f"api_key:{api_key.api_key}")
    return {"message": "API key deleted successfully"}


@router.post("/change-password")
async def change_password(
    payload: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """修改当前账户密码。"""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    current_user.password_hash = get_password_hash(payload.new_password)
    await db.commit()
    return {"message": "Password changed successfully"}
