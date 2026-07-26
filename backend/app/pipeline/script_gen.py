"""
Генерация сценария: разбиваем тему/бриф (и, если дана ссылка, структуру
референса) на сцены. Каждая сцена = { voiceover, image_prompt, duration_sec }.
"""
import json
from anthropic import Anthropic
from ..config import settings

SYSTEM_PROMPT = """Ты — сценарист коротких вертикальных видео (Reels/Shorts).
Разбей заданную тему на 4-6 сцен для ролика длиной 30-45 секунд.
Хук в первой сцене должен цеплять за 1-2 секунды.
Верни СТРОГО JSON-массив без пояснений, формат каждого элемента:
{
  "voiceover": "текст для озвучки этой сцены (1-2 короткие фразы)",
  "image_prompt": "детальный промпт для генерации кадра (на английском, для image-модели)",
  "duration_sec": 5
}"""


def generate_script(topic: str, source_url: str | None = None) -> list[dict]:
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_prompt = f"Тема ролика: {topic}"
    if source_url:
        user_prompt += (
            f"\nРеференс (пойми механику хука/структуры, но не копируй дословно): {source_url}"
        )

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = "".join(block.text for block in resp.content if block.type == "text")
    text = text.strip().strip("`")
    if text.startswith("json"):
        text = text[4:]

    scenes = json.loads(text)
    return scenes
