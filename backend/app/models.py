import uuid
import datetime as dt
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


def gen_id():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)

    # Stripe
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, default="inactive")  # inactive|active|past_due|canceled
    subscription_current_period_end = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)

    jobs = relationship("Job", back_populates="user")

    @property
    def has_active_subscription(self) -> bool:
        if self.is_admin:
            return True
        return self.subscription_status == "active"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # вход
    source_url = Column(String, nullable=True)   # ссылка на референс-ролик (опционально)
    topic = Column(Text, nullable=False)          # тема/ниша/бриф

    # статус пайплайна: queued -> script -> images -> voice -> video -> assembling -> done | error
    status = Column(String, default="queued")
    error = Column(Text, nullable=True)

    script_json = Column(Text, nullable=True)     # сценарий по сценам (json)
    final_video_path = Column(String, nullable=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    user = relationship("User", back_populates="jobs")
