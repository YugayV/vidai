import datetime as dt
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, security
from ..database import get_db
from ..config import settings

router = APIRouter(prefix="/billing", tags=["billing"])
stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/checkout")
def create_checkout_session(
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Создаёт Stripe Checkout Session на месячную подписку и возвращает ссылку на оплату."""
    if not settings.STRIPE_PRICE_ID:
        raise HTTPException(500, "STRIPE_PRICE_ID не настроен в .env")

    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email)
        user.stripe_customer_id = customer.id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
        metadata={"user_id": user.id},
    )
    return {"checkout_url": session.url}


@router.post("/portal")
def create_portal_session(
    user: models.User = Depends(security.get_current_user),
):
    """Ссылка на Customer Portal — отмена/смена карты для подписчика."""
    if not user.stripe_customer_id:
        raise HTTPException(400, "У пользователя ещё нет Stripe-профиля")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=settings.STRIPE_SUCCESS_URL,
    )
    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Слушает события Stripe. В Stripe Dashboard -> Webhooks укажи:
    <твой домен>/billing/webhook
    События: checkout.session.completed, customer.subscription.updated,
    customer.subscription.deleted, invoice.payment_failed
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(400, "Неверная подпись webhook")

    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        user_id = obj.get("metadata", {}).get("user_id")
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            user.stripe_subscription_id = obj.get("subscription")
            user.subscription_status = "active"
            db.commit()

    elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        customer_id = obj.get("customer")
        user = db.query(models.User).filter(models.User.stripe_customer_id == customer_id).first()
        if user:
            status_map = {
                "active": "active",
                "trialing": "active",
                "past_due": "past_due",
                "canceled": "canceled",
                "unpaid": "canceled",
            }
            user.subscription_status = status_map.get(obj.get("status"), "inactive")
            period_end = obj.get("current_period_end")
            if period_end:
                user.subscription_current_period_end = dt.datetime.utcfromtimestamp(period_end)
            db.commit()

    elif etype == "invoice.payment_failed":
        customer_id = obj.get("customer")
        user = db.query(models.User).filter(models.User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = "past_due"
            db.commit()

    return {"received": True}
