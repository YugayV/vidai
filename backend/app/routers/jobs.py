from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import subprocess

from .. import models, schemas, security
from ..database import get_db, SessionLocal
from ..pipeline.orchestrator import run_pipeline

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _run_in_background(job_id: str):
    # своя сессия БД, т.к. задача выполняется вне контекста запроса
    db = SessionLocal()
    try:
        run_pipeline(job_id, db)
    finally:
        db.close()


@router.post("", response_model=schemas.JobOut)
def create_job(
    data: schemas.JobCreateIn,
    background_tasks: BackgroundTasks,
    user: models.User = Depends(security.require_subscription),
    db: Session = Depends(get_db),
):
    job = models.Job(
        user_id=user.id,
        topic=data.topic,
        source_url=data.source_url,
        aspect_ratio=data.aspect_ratio,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_in_background, job.id)
    return job


@router.get("", response_model=list[schemas.JobOut])
def list_jobs(
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Job)
        .filter(models.Job.user_id == user.id)
        .order_by(models.Job.created_at.desc())
        .all()
    )


@router.get("/{job_id}", response_model=schemas.JobOut)
def get_job(
    job_id: str,
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(models.Job.id == job_id, models.Job.user_id == user.id).first()
    if not job:
        raise HTTPException(404, "Задача не найдена")
    return job


@router.get("/{job_id}/download")
def download_job(
    job_id: str,
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(models.Job.id == job_id, models.Job.user_id == user.id).first()
    if not job or not job.final_video_path:
        raise HTTPException(404, "Видео ещё не готово")
    return FileResponse(job.final_video_path, media_type="video/mp4", filename=f"{job.id}.mp4")


@router.get("/{job_id}/public/{token}")
def public_download(job_id: str, token: str, db: Session = Depends(get_db)):
    """
    Публичная ссылка на скачивание без авторизации — по ней можно поделиться
    готовым роликом (например, в Telegram) не требуя логина на сайте.
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job or not job.share_token or job.share_token != token or not job.final_video_path:
        raise HTTPException(404, "Ссылка недействительна или видео ещё не готово")
    return FileResponse(job.final_video_path, media_type="video/mp4", filename=f"{job.id}.mp4")


@router.post("/{job_id}/clip")
def clip_job(
    job_id: str,
    data: schemas.ClipIn,
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Вырезает кусок готового ролика по таймкодам (в секундах) — для нарезки на несколько клипов."""
    job = db.query(models.Job).filter(models.Job.id == job_id, models.Job.user_id == user.id).first()
    if not job or not job.final_video_path:
        raise HTTPException(404, "Видео ещё не готово")
    if data.end_sec <= data.start_sec:
        raise HTTPException(400, "Конец отрезка должен быть позже начала")

    out_path = os.path.join(
        os.path.dirname(job.final_video_path),
        f"clip_{int(data.start_sec)}_{int(data.end_sec)}.mp4",
    )
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(data.start_sec),
        "-to", str(data.end_sec),
        "-i", job.final_video_path,
        "-c:v", "libx264", "-c:a", "aac",  # реэнкод — чтобы обрезка была точной, не по ключевым кадрам
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(out_path):
        raise HTTPException(500, f"Не получилось обрезать видео: {result.stderr[-500:]}")

    return FileResponse(out_path, media_type="video/mp4", filename=f"clip_{job.id}.mp4")
