"""
Генерация ключевого кадра для сцены через Gemini image-модель (Nano Banana).

Проверено по актуальной документации: https://ai.google.dev/gemini-api/docs/image-generation
Обязательно нужен config={"response_modalities": ["IMAGE"]}, иначе модель
может вернуть только текст.
"""
import os
from google import genai
from ..config import settings


def generate_image(prompt: str, out_path: str, aspect_ratio: str = "9:16") -> str:
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    response = client.models.generate_content(
        model=settings.IMAGE_MODEL,
        contents=f"{prompt}\n\nAspect ratio: {aspect_ratio}, vertical mobile video frame.",
        config={"response_modalities": ["IMAGE"]},
    )

    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) is not None:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(part.inline_data.data)
            return out_path

    raise RuntimeError("Модель не вернула изображение — проверь промпт/квоту/модель")
