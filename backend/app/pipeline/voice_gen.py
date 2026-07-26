import os
from elevenlabs.client import ElevenLabs
from ..config import settings


def generate_voice(text: str, out_path: str) -> str:
    client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

    audio = client.text_to_speech.convert(
        voice_id=settings.ELEVENLABS_VOICE_ID,
        model_id="eleven_multilingual_v2",
        text=text,
    )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return out_path
