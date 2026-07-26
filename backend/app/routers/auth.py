from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenOut)
def register(data: schemas.RegisterIn, db: Session = Depends(get_db)):
    if data.invite_code != settings.INVITE_CODE:
        raise HTTPException(status_code=403, detail="Неверный инвайт-код")

    existing = db.query(models.User).filter(models.User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Такой email уже зарегистрирован")

    # Первый зарегистрированный пользователь = ты, автоматически админ с безлимитным доступом
    is_first_user = db.query(models.User).count() == 0

    user = models.User(
        email=data.email,
        hashed_password=security.hash_password(data.password),
        is_admin=is_first_user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = security.create_access_token(user.id)
    return schemas.TokenOut(access_token=token)


@router.post("/login", response_model=schemas.TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not security.verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    token = security.create_access_token(user.id)
    return schemas.TokenOut(access_token=token)


@router.get("/me", response_model=schemas.MeOut)
def me(user: models.User = Depends(security.get_current_user)):
    return schemas.MeOut(
        id=user.id,
        email=user.email,
        subscription_status=user.subscription_status,
        has_active_subscription=user.has_active_subscription,
    )
