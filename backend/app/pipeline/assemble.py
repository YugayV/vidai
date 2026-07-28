"""
Собираем сцены (видео-клип без звука + отдельная озвучка) в один ролик.
Использует системный ffmpeg через subprocess — убедись, что ffmpeg установлен
(в Docker-образе он уже есть, см. Dockerfile).
"""
import os
import subprocess


def mux_scene(video_path: str, voice_path: str, out_path: str) -> str:
    """Накладывает озвучку на видео-клип сцены (обрезает по короткой дорожке)."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", voice_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def concat_scenes(scene_paths: list[str], out_path: str) -> str:
    """Склеивает готовые сцены (видео+звук) в финальный ролик."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    list_file = out_path + ".txt"
    with open(list_file, "w") as f:
        for p in scene_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(list_file)
    return out_path
