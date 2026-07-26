import hashlib
import hmac
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from .. import models, schemas, security
from ..database import get_db
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token_for(user: models.User) -> schemas.TokenOut:
    return schemas.TokenOut(access_token=security.create_access_token(user.id))


def _create_user(db: Session, email: str, provider: str, hashed_password: str | None) -> models.User:
    is_first_user = db.query(models.User).count() == 0
    user = models.User(
        email=email,
        hashed_password=hashed_password,
        auth_provider=provider,
        is_admin=is_first_user,  # первый зарегистрированный = ты = админ
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/register", response_model=schemas.TokenOut)
def register(data: schemas.RegisterIn, db: Session = Depends(get_db)):
    if data.invite_code != settings.INVITE_CODE:
        raise HTTPException(status_code=403, detail="Неверный инвайт-код")

    existing = db.query(models.User).filter(models.User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Такой email уже зарегистрирован")

    user = _create_user(db, data.email, "email", security.hash_password(data.password))
    return _issue_token_for(user)


@router.post("/login", response_model=schemas.TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not user.hashed_password or not security.verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    return _issue_token_for(user)


@router.post("/google", response_model=schemas.TokenOut)
def google_login(data: schemas.GoogleAuthIn, db: Session = Depends(get_db)):
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(500, "GOOGLE_OAUTH_CLIENT_ID не настроен на сервере")

    try:
        idinfo = google_id_token.verify_oauth2_token(
            data.id_token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(400, "Невалидный Google-токен")

    email = idinfo.get("email")
    if not email or not idinfo.get("email_verified"):
        raise HTTPException(400, "Google не подтвердил email")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        if data.invite_code != settings.INVITE_CODE:
            raise HTTPException(403, "Неверный инвайт-код")
        user = _create_user(db, email, "google", hashed_password=None)

    return _issue_token_for(user)


@router.post("/telegram", response_model=schemas.TokenOut)
def telegram_login(data: schemas.TelegramAuthIn, db: Session = Depends(get_db)):
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(500, "TELEGRAM_BOT_TOKEN не настроен на сервере")

    # Проверка подписи данных от Telegram Login Widget.
    # https://core.telegram.org/widgets/login#checking-authorization
    payload = data.model_dump(exclude={"hash", "invite_code"})
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()) if v is not None)
    secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, data.hash):
        raise HTTPException(403, "Подпись Telegram не прошла проверку")

    if time.time() - data.auth_date > 86400:
        raise HTTPException(403, "Данные авторизации Telegram устарели, попробуй снова")

    pseudo_email = f"tg_{data.id}@telegram.local"
    user = db.query(models.User).filter(models.User.email == pseudo_email).first()
    if not user:
        if data.invite_code != settings.INVITE_CODE:
            raise HTTPException(403, "Неверный инвайт-код")
        user = _create_user(db, pseudo_email, "telegram", hashed_password=None)

    return _issue_token_for(user)


@router.get("/me", response_model=schemas.MeOut)
def me(user: models.User = Depends(security.get_current_user)):
    return schemas.MeOut(
        id=user.id,
        email=user.email,
        subscription_status=user.subscription_status,
        has_active_subscription=user.has_active_subscription,
        is_admin=user.is_admin,
    )
