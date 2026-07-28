import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, security
from ..database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])

TIMELINE_DAYS = 14


def _timeline(jobs: list[models.Job], days: int = TIMELINE_DAYS) -> list[dict]:
    counts = defaultdict(int)
    for j in jobs:
        counts[j.created_at.strftime("%Y-%m-%d")] += 1

    today = dt.datetime.utcnow()
    return [
        {
            "date": (today - dt.timedelta(days=i)).strftime("%Y-%m-%d"),
            "count": counts.get((today - dt.timedelta(days=i)).strftime("%Y-%m-%d"), 0),
        }
        for i in range(days - 1, -1, -1)
    ]


def _avg_duration(jobs: list[models.Job]) -> float | None:
    durations = [
        (j.finished_at - j.started_at).total_seconds()
        for j in jobs
        if j.started_at and j.finished_at
    ]
    return round(sum(durations) / len(durations), 1) if durations else None


@router.get("/me")
def my_analytics(
    user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    jobs = db.query(models.Job).filter(models.Job.user_id == user.id).all()
    done = sum(1 for j in jobs if j.status == "done")
    error = sum(1 for j in jobs if j.status == "error")

    return {
        "total": len(jobs),
        "done": done,
        "error": error,
        "in_progress": len(jobs) - done - error,
        "avg_duration_sec": _avg_duration(jobs),
        "timeline": _timeline(jobs),
    }


@router.get("/overview")
def overview_analytics(
    admin: models.User = Depends(security.require_admin),
    db: Session = Depends(get_db),
):
    jobs = db.query(models.Job).all()
    users = db.query(models.User).all()
    email_by_id = {u.id: u.email for u in users}

    done = sum(1 for j in jobs if j.status == "done")
    error = sum(1 for j in jobs if j.status == "error")

    per_user = defaultdict(int)
    for j in jobs:
        per_user[j.user_id] += 1

    top_users = sorted(
        ({"email": email_by_id.get(uid, "?"), "jobs": count} for uid, count in per_user.items()),
        key=lambda x: -x["jobs"],
    )[:10]

    return {
        "total_users": len(users),
        "active_subscriptions": sum(1 for u in users if u.subscription_status == "active"),
        "total_jobs": len(jobs),
        "done": done,
        "error": error,
        "in_progress": len(jobs) - done - error,
        "avg_duration_sec": _avg_duration(jobs),
        "timeline": _timeline(jobs),
        "top_users": top_users,
    }
