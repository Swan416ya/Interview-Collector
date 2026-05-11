"""Update question wrongbook state after a new graded practice attempt (not idempotent replays)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.question import PracticeRecord, Question


def update_wrongbook_after_attempt(db: Session, question_id: int, new_score: int) -> None:
    """
    Call only after a new PracticeRecord row is flushed for this question.
    - Admit: score <= WRONGBOOK_ADMIT_MAX_SCORE, optionally requiring N consecutive lows.
    - Discharge (only if currently active): last M attempts all >= WRONGBOOK_DISCHARGE_MIN_SCORE.
    """
    q = db.get(Question, question_id)
    if not q:
        return

    admit_max = max(0, min(10, int(settings.wrongbook_admit_max_score)))
    consec_need = max(1, int(settings.wrongbook_admit_consecutive_low))
    streak_need = max(1, int(settings.wrongbook_discharge_streak))
    min_ok = max(0, min(10, int(settings.wrongbook_discharge_min_score)))
    now = datetime.utcnow()

    should_admit = False
    if new_score <= admit_max:
        if consec_need <= 1:
            should_admit = True
        else:
            recs = db.scalars(
                select(PracticeRecord)
                .where(PracticeRecord.question_id == question_id)
                .order_by(PracticeRecord.id.desc())
                .limit(consec_need)
            ).all()
            should_admit = len(recs) >= consec_need and all(int(r.ai_score) <= admit_max for r in recs)

    if should_admit:
        q.wrongbook_active = True
        q.wrongbook_last_wrong_at = now
        if q.wrongbook_entered_at is None:
            q.wrongbook_entered_at = now
        q.wrongbook_cleared_at = None
        return

    if not q.wrongbook_active:
        return

    recs = db.scalars(
        select(PracticeRecord)
        .where(PracticeRecord.question_id == question_id)
        .order_by(PracticeRecord.id.desc())
        .limit(streak_need)
    ).all()
    if len(recs) < streak_need:
        return
    if all(int(r.ai_score) >= min_ok for r in recs):
        q.wrongbook_active = False
        q.wrongbook_cleared_at = now


def manual_add_to_wrongbook(db: Session, question: Question) -> None:
    now = datetime.utcnow()
    question.wrongbook_active = True
    question.wrongbook_last_wrong_at = now
    if question.wrongbook_entered_at is None:
        question.wrongbook_entered_at = now
    question.wrongbook_cleared_at = None
