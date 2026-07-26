import datetime as dt
from typing import Optional
from pydantic import BaseModel, EmailStr


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    invite_code: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    id: str
    email: EmailStr
    subscription_status: str
    has_active_subscription: bool

    class Config:
        from_attributes = True


class JobCreateIn(BaseModel):
    topic: str
    source_url: Optional[str] = None


class JobOut(BaseModel):
    id: str
    topic: str
    source_url: Optional[str]
    status: str
    error: Optional[str]
    final_video_path: Optional[str]
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        from_attributes = True
