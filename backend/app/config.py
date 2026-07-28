"""
Вся конфигурация читается из .env (см. .env.example).
Ничего секретного не хардкодим в коде.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Общие ---
    APP_NAME: str = "ContentForge"
    SECRET_KEY: str = "change-me-please"  # для подписи JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # неделя
    DATABASE_URL: str = "sqlite:///./storage/app.db"
    STORAGE_DIR: str = "./storage"

    # --- Приглашение для регистрации знакомых (простая защита от чужих) ---
    # Если оставить пустым — регистрация открыта без кода (удобно, пока
    # раздаёшь программу вручную). Впиши код сюда, когда решишь закрыть вход.
    INVITE_CODE: str = ""

    # --- Google OAuth (кнопка "Войти через Google") ---
    # Google Cloud Console -> APIs & Services -> Credentials -> OAuth client ID
    # -> Web application -> Authorized JavaScript origins = твой домен
    GOOGLE_OAUTH_CLIENT_ID: str = ""

    # --- Telegram Login Widget ---
    # Бот создаётся у @BotFather; затем команда /setdomain -> указать домен
    # сайта (виджет не будет работать без привязанного домена).
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""

    # --- LLM для сценария ---
    ANTHROPIC_API_KEY: str = ""

    # --- Google Gemini (Nano Banana = картинки, Veo = видео) ---
    GOOGLE_API_KEY: str = ""
    IMAGE_MODEL: str = "gemini-2.5-flash-image"
    VIDEO_MODEL: str = "veo-3.1-generate-preview"

    # --- ElevenLabs (озвучка) ---
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = ""

    # --- Stripe (подписка для знакомых) ---
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID: str = ""  # ID цены месячной подписки в Stripe Dashboard
    STRIPE_SUCCESS_URL: str = "http://localhost:8000/?checkout=success"
    STRIPE_CANCEL_URL: str = "http://localhost:8000/?checkout=cancel"


settings = Settings()
