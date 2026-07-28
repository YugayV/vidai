import datetime as dt
from typing import Optional
from pydantic import BaseModel


class RegisterIn(BaseModel):
    email: str
    password: str
    invite_code: str = ""


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    id: str
    email: str
    subscription_status: str
    has_active_subscription: bool
    is_admin: bool

    class Config:
        from_attributes = True


class GoogleAuthIn(BaseModel):
    id_token: str
    invite_code: str = ""


class TelegramAuthIn(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str
    invite_code: str = ""


class AdminUserOut(BaseModel):
    id: str
    email: str
    is_admin: bool
    auth_provider: str
    subscription_status: str
    created_at: dt.datetime

    class Config:
        from_attributes = True


class JobCreateIn(BaseModel):
    topic: str
    source_url: Optional[str] = None
    aspect_ratio: str = "9:16"


class ClipIn(BaseModel):
    start_sec: float
    end_sec: float


class JobOut(BaseModel):
    id: str
    topic: str
    source_url: Optional[str]
    aspect_ratio: str
    status: str
    error: Optional[str]
    final_video_path: Optional[str]
    share_token: Optional[str]
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        from_attributes = True
