"""
Оживляем статичный кадр в короткий видео-клип через Veo (image-to-video).

ВАЖНО: Veo — асинхронная long-running операция в Gemini API/Vertex AI.
Точные имена методов могут отличаться в актуальной версии SDK — сверься с:
https://ai.google.dev/gemini-api/docs/video
Каркас ниже реализует общий паттерн: submit -> poll -> download.
"""
import os
import time
from google import genai
from google.genai import types
from ..config import settings


def generate_video_from_image(image_path: str, prompt: str, out_path: str, duration_sec: int = 5) -> str:
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    operation = client.models.generate_videos(
        model=settings.VIDEO_MODEL,
        prompt=prompt,
        image=types.Image(image_bytes=image_bytes, mime_type="image/png"),
    )

    # Veo работает асинхронно — опрашиваем статус операции
    while not operation.done:
        time.sleep(10)
        operation = client.operations.get(operation)

    video = operation.response.generated_videos[0]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    client.files.download(file=video.video)
    video.video.save(out_path)
    return out_path
