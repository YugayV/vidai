from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from anthropic import Anthropic

from .. import models, security
from ..config import settings

router = APIRouter(prefix="/assistant", tags=["assistant"])

SYSTEM_PROMPT = """Ты — ассистент-продюсер контента для Instagram Reels.
Ниша: обучение людей и бизнеса нейросетям (генерация видео/картинок,
автоматизация контента, AI-маркетинг). Помогаешь придумывать темы, хуки
и короткие сценарии по формуле: Хук (0-2 сек) → Проблема/интрига →
Демонстрация решения через AI-инструмент → Призыв в Telegram.
Отвечай коротко, конкретно, разговорным экспертным тоном, без канцелярита.
Когда предлагаешь готовую тему для ролика — заверши ответ отдельной строкой
строго в формате: ТЕМА: <короткая формулировка темы/брифа>"""


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatIn(BaseModel):
    messages: list[ChatMessage]


@router.post("/chat")
def chat(
    data: ChatIn,
    user: models.User = Depends(security.require_subscription),
):
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY не настроен на сервере")
    if not data.messages:
        raise HTTPException(400, "Пустое сообщение")

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": m.role, "content": m.content} for m in data.messages],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    return {"reply": text}
