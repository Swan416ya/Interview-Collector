from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="未分类")
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    reference_answer: Mapped[str] = mapped_column(Text, default="")
    mastery_score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


class PracticeRecord(Base):
    __tablename__ = "practice_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    question_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_answer: Mapped[str] = mapped_column(Text, default="")
    ai_answer: Mapped[str] = mapped_column(Text, default="")
    ai_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-10
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    total_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100, ten questions total
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

