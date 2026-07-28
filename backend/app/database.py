import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

os.makedirs(settings.STORAGE_DIR, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_light_migrations():
    """
    create_all() создаёт только отсутствующие ТАБЛИЦЫ, но не добавляет новые
    колонки в уже существующие (актуально для SQLite на volume в Railway).
    Здесь добиваем недостающие колонки вручную, без Alembic — для личного
    проекта этого достаточно.
    """
    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return  # таблица создастся заново через create_all со всеми колонками

    existing = {c["name"] for c in inspector.get_columns("jobs")}
    to_add = {
        "share_token": "VARCHAR",
        "started_at": "DATETIME",
        "finished_at": "DATETIME",
        "aspect_ratio": "VARCHAR DEFAULT '9:16'",
    }
    with engine.begin() as conn:
        for name, ddl_type in to_add.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE jobs ADD COLUMN {name} {ddl_type}"))
        # у старых строк share_token пуст — генерим, чтобы публичные ссылки работали
        conn.execute(
            text("UPDATE jobs SET share_token = lower(hex(randomblob(16))) WHERE share_token IS NULL")
        )
