"""
Оживляем статичный кадр в короткий видео-клип через Veo (image-to-video).

Актуальный паттерн SDK (проверено по ai.google.dev/gemini-api/docs/veo,
октябрь 2025 — Veo 3.1): types.Image.from_file + generate_videos +
поллинг operation + video.save(). Раньше здесь был неточный вызов —
поправлено под реальную сигнатуру SDK.

Звук отключаем (generate_audio=False): озвучку добавляем отдельно через
ElevenLabs/Lumean на этапе сборки, два источника звука не нужны.
"""
import os
import time
from google import genai
from google.genai import types
from ..config import settings


def generate_video_from_image(
    image_path: str,
    prompt: str,
    out_path: str,
    duration_sec: int = 5,
    aspect_ratio: str = "9:16",
) -> str:
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    image = types.Image.from_file(image_path)

    operation = client.models.generate_videos(
        model=settings.VIDEO_MODEL,
        prompt=prompt,
        image=image,
        config=types.GenerateVideosConfig(
            number_of_videos=1,
            duration_seconds=duration_sec,
            aspect_ratio=aspect_ratio,
            generate_audio=False,
            enhance_prompt=True,
        ),
    )

    # Veo — асинхронная long-running операция, опрашиваем статус
    while not operation.done:
        time.sleep(10)
        operation = client.operations.get(operation)

    if operation.error:
        raise RuntimeError(f"Veo вернул ошибку: {operation.error}")

    video = operation.response.generated_videos[0].video
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    video.save(out_path)
    return out_path
