"""Pydantic 请求/响应模型"""

import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum


# ============ 认证 ============

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if len(v) > 5 and not re.match(pattern, v):
            raise ValueError("邮箱格式不正确")
        return v.strip().lower()

class LoginRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=128)
    device_fingerprint: str = Field(default="")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

class RefreshRequest(BaseModel):
    device_fingerprint: str = Field(default="")


# ============ 用户 ============

class UserProfile(BaseModel):
    id: int
    email: str
    username: str
    role: str
    status: str
    created_at: Optional[datetime] = None

    class Config: from_attributes = True


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = Field(default=None, min_length=2, max_length=100)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


class SendVerifyCodeRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    purpose: str = Field(default="register")  # "register" | "reset_password"

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        if v not in ("register", "reset_password"):
            raise ValueError("用途只能是 register 或 reset_password")
        return v

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if len(v) > 5 and not re.match(pattern, v):
            raise ValueError("邮箱格式不正确")
        return v.strip().lower()


class VerifyEmailRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    code: str = Field(..., min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6, max_length=128)


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=128)


# ============ 订阅 ============

class PlanEnum(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"

class SubscriptionStatus(BaseModel):
    plan: str
    status: str
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    auto_renew: bool = False

    class Config: from_attributes = True

class CreateOrderRequest(BaseModel):
    plan: PlanEnum

class PaymentCallbackRequest(BaseModel):
    payjs_order_id: str
    status: str  # "paid" or "cancelled"


# ============ 试用次数 ============

class TrialSyncRequest(BaseModel):
    device_fingerprint: str = Field(..., min_length=1)
    remaining: int = Field(..., ge=0)

class TrialConsumeRequest(BaseModel):
    device_fingerprint: str = Field(..., min_length=1)

class TrialSyncResponse(BaseModel):
    remaining: int
    total_used: int
    synced: bool


# ============ 用量 ============

class UsageLogRequest(BaseModel):
    text_length: int = 0
    duration_seconds: float = 0
    device: str = ""


# ============ 公告 ============

class AnnouncementResponse(BaseModel):
    id: int
    title: str
    body: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config: from_attributes = True

class AnnouncementCreateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    body: str = Field(..., min_length=1)
    is_active: bool = True

class AnnouncementUpdateRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    is_active: Optional[bool] = None


# ============ 管理后台 ============

class AdminUserUpdateRequest(BaseModel):
    status: Optional[str] = None  # active / disabled / banned
    role: Optional[str] = None

class AdminSubscriptionCreateRequest(BaseModel):
    user_id: int
    plan: PlanEnum
    duration_days: Optional[int] = None  # 手动指定天数（不设则用默认）

class AdminStatsResponse(BaseModel):
    total_users: int
    active_subscriptions: int
    total_synthesis_count: int
    pending_orders: int

class UserListItem(BaseModel):
    id: int
    email: str
    username: str
    role: str
    status: str
    subscription_plan: Optional[str] = None
    subscription_status: Optional[str] = None
    trial_remaining: int = 0
    created_at: Optional[datetime] = None

    class Config: from_attributes = True


class UsageStatsResponse(BaseModel):
    total_syntheses: int = 0
    total_duration: float = 0
    month_syntheses: int = 0
    month_duration: float = 0
    account_age_days: int = 0


class SessionItem(BaseModel):
    id: int
    device_fingerprint: str
    created_at: Optional[datetime] = None
    is_current: bool = False

    class Config: from_attributes = True


class PaymentHistoryItem(BaseModel):
    id: int
    plan: str
    amount: float
    status: str
    payjs_order_id: str = ""
    paid_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config: from_attributes = True
