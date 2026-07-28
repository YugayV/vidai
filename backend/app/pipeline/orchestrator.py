import json
import os
import traceback
import datetime as dt

from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from . import script_gen, image_gen, video_gen, voice_gen, assemble


def _set_status(db: Session, job: models.Job, status: str, error: str | None = None):
    job.status = status
    job.error = error
    if status in ("done", "error"):
        job.finished_at = dt.datetime.utcnow()
    db.commit()


def run_pipeline(job_id: str, db: Session):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        return

    job.started_at = dt.datetime.utcnow()
    db.commit()

    job_dir = os.path.join(settings.STORAGE_DIR, "jobs", job.id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        # 1. Сценарий
        _set_status(db, job, "script")
        scenes = script_gen.generate_script(job.topic, job.source_url)
        job.script_json = json.dumps(scenes, ensure_ascii=False)
        db.commit()

        scene_final_paths = []

        for i, scene in enumerate(scenes):
            # 2. Кадр
            _set_status(db, job, f"images:{i+1}/{len(scenes)}")
            img_path = os.path.join(job_dir, f"scene_{i}.png")
            image_gen.generate_image(scene["image_prompt"], img_path, aspect_ratio=job.aspect_ratio)

            # 3. Видео из кадра
            _set_status(db, job, f"video:{i+1}/{len(scenes)}")
            vid_path = os.path.join(job_dir, f"scene_{i}.mp4")
            video_gen.generate_video_from_image(
                img_path, scene["image_prompt"], vid_path,
                duration_sec=scene.get("duration_sec", 5),
                aspect_ratio=job.aspect_ratio,
            )

            # 4. Озвучка
            _set_status(db, job, f"voice:{i+1}/{len(scenes)}")
            voice_path = os.path.join(job_dir, f"scene_{i}.mp3")
            voice_gen.generate_voice(scene["voiceover"], voice_path)

            # 5. Наложение звука на клип сцены
            scene_final = os.path.join(job_dir, f"scene_{i}_final.mp4")
            assemble.mux_scene(vid_path, voice_path, scene_final)
            scene_final_paths.append(scene_final)

        # 6. Финальная склейка
        _set_status(db, job, "assembling")
        final_path = os.path.join(job_dir, "final.mp4")
        assemble.concat_scenes(scene_final_paths, final_path)

        job.final_video_path = final_path
        _set_status(db, job, "done")

    except Exception as e:
        _set_status(db, job, "error", error=f"{e}\n{traceback.format_exc()}")
