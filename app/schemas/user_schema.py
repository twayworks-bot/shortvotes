from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class UserIdentifyRequest(BaseModel):
    unique_key: Optional[str] = None
    user_name: Optional[str] = None

class UserRegisterRequest(BaseModel):
    user_name: str = Field(..., min_length=1, max_length=64)
    force_reset: Optional[bool] = False  # 기존 유저 리셋 후 등록 여부

class UserResponse(BaseModel):
    id: str  # Unique Key
    event_id: str
    user_name: str
    created_at: datetime
    last_seen_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

class IdentifyResult(BaseModel):
    status: str  # VALID, EXPIRED, NOT_FOUND, NAME_EXISTS, LIMIT_EXCEEDED
    message: str
    user: Optional[UserResponse] = None
    unique_key: Optional[str] = None
