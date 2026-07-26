from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(
    admin: models.User = Depends(security.require_admin),
    db: Session = Depends(get_db),
):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.post("/users/{user_id}/grant")
def grant_access(
    user_id: str,
    admin: models.User = Depends(security.require_admin),
    db: Session = Depends(get_db),
):
    """Выдать доступ вручную, без оплаты через Stripe (например, самому себе или другу)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    user.subscription_status = "active"
    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/revoke")
def revoke_access(
    user_id: str,
    admin: models.User = Depends(security.require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    if user.is_admin:
        raise HTTPException(400, "Нельзя отозвать доступ у админа")
    user.subscription_status = "inactive"
    db.commit()
    return {"ok": True}


@router.get("/jobs", response_model=list[schemas.JobOut])
def list_all_jobs(
    admin: models.User = Depends(security.require_admin),
    db: Session = Depends(get_db),
):
    return db.query(models.Job).order_by(models.Job.created_at.desc()).limit(200).all()
