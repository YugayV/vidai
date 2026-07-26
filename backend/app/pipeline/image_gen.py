"""
Генерация ключевого кадра для сцены через Gemini image-модель.

ВАЖНО: имя модели/метод SDK для image-генерации у Google меняются со временем.
Проверь актуальный вызов в документации: https://ai.google.dev/gemini-api/docs/image-generation
Ниже — рабочий каркас под google-genai SDK на момент написания.
"""
import os
from google import genai
from ..config import settings


def generate_image(prompt: str, out_path: str) -> str:
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    response = client.models.generate_content(
        model=settings.IMAGE_MODEL,
        contents=[prompt],
    )

    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) is not None:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(part.inline_data.data)
            return out_path

    raise RuntimeError("Модель не вернула изображение — проверь промпт/квоту/модель")
