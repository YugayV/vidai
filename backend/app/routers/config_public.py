from fastapi import APIRouter
from ..config import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def public_config():
    return {
        "google_client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "telegram_bot_username": settings.TELEGRAM_BOT_USERNAME,
    }
