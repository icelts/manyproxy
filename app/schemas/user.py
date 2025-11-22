from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    balance: float
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    is_admin: bool = False


class TokenData(BaseModel):
    username: Optional[str] = None


class APIKeyBase(BaseModel):
    name: Optional[str] = None
    rate_limit: Optional[int] = 1000


class APIKeyCreate(APIKeyBase):
    pass


class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    rate_limit: Optional[int] = None
    is_active: Optional[bool] = None


class APIKeyResponse(APIKeyBase):
    id: int
    api_key: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class APIKeyRotate(BaseModel):
    api_key: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
