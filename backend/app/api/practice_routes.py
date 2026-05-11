import logging
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
import zoneinfo

from app.core.database import get_db, is_sqlite
from app.models.question import PracticeRecord, PracticeSession, Question
from app.schemas.practice import (
    ALLOWED_SESSION_SIZES,
    PracticeActivityDayOut,
    PracticeActivityResponse,
    PracticeCategoriesResponse,
    PracticeRecordFeedItem,
    PracticeRecordFeedPage,
    PracticeSkipRequest,
    PracticeSessionCustomStartRequest,
    PracticeSessionOut,
    PracticeSessionStartResponse,
    PracticeSessionSummaryResponse,
    PracticeSubmitResponse,
    PracticeSubmitRequest,
    WrongbookManualAddRequest,
    WrongbookPageOut,
)
from app.schemas.question import QuestionOut
from app.core.config import settings
from app.services.ai_service import call_doubao_grade
from app.services.session_summary_service import generate_session_summary_if_needed, parse_stored_feedback
from app.services.wrongbook_service import manual_add_to_wrongbook, update_wrongbook_after_attempt

router = APIRouter(prefix="/api/practice", tags=["practice"])
logger = logging.getLogger(__name__)

try:
    _ACTIVITY_TZ = zoneinfo.ZoneInfo("Asia/Shanghai")
except zoneinfo.ZoneInfoNotFoundError:
    _ACTIVITY_TZ = timezone(timedelta(hours=8))
_NUM_WEEKS = 53


def _coerce_sql_date_value(val) -> date:
    """Normalize DATE / string from SQLite (str) or PostgreSQL (date) etc."""
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()[:10]
    return date.fromisoformat(s)


def _sunday_start_of_week(d: date) -> date:
    # Monday=0 .. Sunday=6 in Python; we want week starting Sunday (GitHub-style columns).
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _count_level(n: int) -> int:
    """Match frontend heatmap: 0 gray; 1–9 light; 10–19 mid; 20–49 high; 50+ darkest."""
    if n <= 0:
        return 0
    if n < 10:
        return 1
    if n < 20:
        return 2
    if n < 50:
        return 3
    return 4


@router.get("/activity", response_model=PracticeActivityResponse)
def practice_activity_heatmap(db: Session = Depends(get_db)):
    """
    Dense last-53-week window (371 days), Sunday-first columns.

    Each cell's **count** uses the **calendar date of `created_at` as stored in the DB**
    (SQL `date(created_at)` / SQLite `date(created_at)`), **without** re-interpreting naive
    timestamps as UTC then shifting to Shanghai. That matches raw-SQL row counts like
    `WHERE date(created_at) = '2026-04-11'` and avoids off-by-one vs. DB browser totals.

    `today` (future cells greyed) still uses Asia/Shanghai wall date for UX.
    """
    today = datetime.now(_ACTIVITY_TZ).date()
    end_sunday = _sunday_start_of_week(today)
    start_sunday = end_sunday - timedelta(weeks=_NUM_WEEKS - 1)
    end_last = start_sunday + timedelta(days=_NUM_WEEKS * 7 - 1)

    day_key = func.date(PracticeRecord.created_at)
    agg_stmt = (
        select(day_key, func.count(PracticeRecord.id))
        .where(day_key >= start_sunday, day_key <= end_last)
        .group_by(day_key)
    )
    agg_rows = db.execute(agg_stmt).all()
    per_day: Counter[date] = Counter()
    for day_val, cnt in agg_rows:
        per_day[_coerce_sql_date_value(day_val)] += int(cnt)

    days_out: list[PracticeActivityDayOut] = []
    total_questions = 0
    active_days = 0
    d = start_sunday
    while d <= end_last:
        c = int(per_day.get(d, 0))
        total_questions += c
        if c > 0:
            active_days += 1
        ds = d.isoformat()
        if d > today:
            days_out.append(PracticeActivityDayOut(date=ds, count=0, level=0))
        else:
            days_out.append(PracticeActivityDayOut(date=ds, count=c, level=_count_level(c)))
        d += timedelta(days=1)

    return PracticeActivityResponse(
        timezone="storage-date(created_at)",
        start_date=start_sunday.isoformat(),
        end_date=end_last.isoformat(),
        today=today.isoformat(),
        total_questions=total_questions,
        active_days=active_days,
        days=days_out,
    )


@router.get("/records", response_model=PracticeRecordFeedPage)
def list_all_practice_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    shanghai_date: str | None = Query(
        default=None,
        description="YYYY-MM-DD; same as SQL date(created_at) and heatmap cell (storage calendar day)",
    ),
    db: Session = Depends(get_db),
):
    """
    Paginated log of every practice row (session submit/skip, daily submit).
    Use `shanghai_date` to reconcile row count with GET /api/practice/activity for that date.
    """
    base_filter = []
    if shanghai_date is not None and shanghai_date.strip():
        try:
            d = date.fromisoformat(shanghai_date.strip())
        except ValueError:
            raise HTTPException(status_code=400, detail="shanghai_date must be YYYY-MM-DD") from None
        base_filter = [func.date(PracticeRecord.created_at) == d]

    count_stmt = select(func.count(PracticeRecord.id))
    if base_filter:
        count_stmt = count_stmt.where(*base_filter)
    total = int(db.scalar(count_stmt) or 0)

    stmt = (
        select(PracticeRecord, Question.stem)
        .select_from(PracticeRecord)
        .outerjoin(Question, PracticeRecord.question_id == Question.id)
        .order_by(PracticeRecord.id.desc())
    )
    if base_filter:
        stmt = stmt.where(*base_filter)

    offset = (page - 1) * page_size
    rows = db.execute(stmt.offset(offset).limit(page_size)).all()

    items = [
        PracticeRecordFeedItem(
            id=rec.id,
            session_id=rec.session_id,
            question_id=rec.question_id,
            question_stem=(qstem or "").strip() or "（题目已删除）",
            user_answer=rec.user_answer or "",
            ai_score=int(rec.ai_score),
            created_at=rec.created_at,
        )
        for rec, qstem in rows
    ]
    return PracticeRecordFeedPage(total=total, page=page, page_size=page_size, items=items)


def _update_mastery_by_formula(question: Question, latest_score_0_10: int) -> None:
    old_mastery = int(question.mastery_score or 0)
    latest_score_100 = max(0, min(10, latest_score_0_10)) * 10
    new_mastery = round(old_mastery * 0.7 + latest_score_100 * 0.3)
    question.mastery_score = max(0, min(100, int(new_mastery)))


def _finalize_session_if_done(db: Session, session: PracticeSession) -> None:
    scores = db.scalars(select(PracticeRecord.ai_score).where(PracticeRecord.session_id == session.id)).all()
    if len(scores) >= session.question_count:
        session.total_score = int(sum(scores))
        session.completed_at = datetime.utcnow()


def _try_session_summary_after_complete(db: Session, session_id: int) -> None:
    """After main transaction commits, best-effort one LLM call for session radar (does not fail the practice API)."""
    sess = db.get(PracticeSession, session_id)
    if not sess or not sess.completed_at or sess.summary_done:
        return
    try:
        generate_session_summary_if_needed(db, sess)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("session_summary failed session_id=%s", session_id)


@router.get("/ping")
def practice_ping() -> dict:
    return {"message": "practice module ready"}


@router.post("/sessions/start", response_model=PracticeSessionStartResponse)
def start_practice_session(
    category: str | None = None,
    count: int = Query(10, description="Number of questions: 5, 10, or 15"),
    pool: str = Query("all", description="all: full bank; wrongbook: only wrongbook_active questions"),
    db: Session = Depends(get_db),
):
    if count not in ALLOWED_SESSION_SIZES:
        raise HTTPException(status_code=400, detail="count must be 5, 10, or 15")
    if pool not in ("all", "wrongbook"):
        raise HTTPException(status_code=400, detail="pool must be all or wrongbook")
    stmt = select(Question)
    if pool == "wrongbook":
        stmt = stmt.where(Question.wrongbook_active.is_(True))
    if category:
        stmt = stmt.where(Question.category == category)
    order_rand = func.random() if is_sqlite else func.rand()
    questions = db.scalars(stmt.order_by(order_rand).limit(count)).all()
    if len(questions) < count:
        scope = f"Category '{category}'" if category else "Question bank (all categories)"
        if pool == "wrongbook":
            scope = f"Wrongbook in {scope}" if category else "Wrongbook (all categories)"
        raise HTTPException(
            status_code=400,
            detail=f"{scope} has only {len(questions)} question(s); need at least {count} to start this session",
        )
    session = PracticeSession(total_score=0, question_count=count)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "questions": questions, "question_count": count}


@router.post("/sessions/start/custom", response_model=PracticeSessionStartResponse)
def start_practice_session_custom(payload: PracticeSessionCustomStartRequest, db: Session = Depends(get_db)):
    unique_ids = list(dict.fromkeys(payload.question_ids))
    n = len(unique_ids)

    questions = db.scalars(select(Question).where(Question.id.in_(unique_ids))).all()
    if len(questions) != n:
        raise HTTPException(status_code=400, detail="Some question ids do not exist")

    # Return in the incoming order so client can keep its planned sequence.
    question_map = {q.id: q for q in questions}
    ordered_questions = [question_map[qid] for qid in unique_ids if qid in question_map]

    session = PracticeSession(total_score=0, question_count=n)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "questions": ordered_questions, "question_count": n}


@router.get("/categories", response_model=PracticeCategoriesResponse)
def list_practice_categories(
    pool: str = Query("all", description="all | wrongbook"),
    db: Session = Depends(get_db),
):
    if pool not in ("all", "wrongbook"):
        raise HTTPException(status_code=400, detail="pool must be all or wrongbook")
    cat_stmt = select(Question.category, func.count(Question.id)).group_by(Question.category)
    if pool == "wrongbook":
        cat_stmt = (
            select(Question.category, func.count(Question.id))
            .where(Question.wrongbook_active.is_(True))
            .group_by(Question.category)
        )
    rows = db.execute(cat_stmt.order_by(Question.category.asc())).all()
    total_stmt = select(func.count()).select_from(Question)
    if pool == "wrongbook":
        total_stmt = total_stmt.where(Question.wrongbook_active.is_(True))
    total_all = int(db.scalar(total_stmt) or 0)
    categories = [
        {
            "category": category or "未分类",
            "total_questions": int(total),
            "selectable": int(total) >= 5,
        }
        for category, total in rows
    ]
    return PracticeCategoriesResponse(categories=categories, total_questions_all=total_all)


@router.post("/sessions/{session_id}/submit", response_model=PracticeSubmitResponse)
def submit_answer(session_id: int, payload: PracticeSubmitRequest, db: Session = Depends(get_db)):
    session = db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")
    q = db.get(Question, payload.question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    existed = db.scalar(
        select(PracticeRecord).where(
            PracticeRecord.session_id == session_id,
            PracticeRecord.question_id == payload.question_id,
        )
    )
    if existed:
        logger.info(
            "practice_submit skip_ai reason=session_duplicate session_id=%s question_id=%s record_id=%s",
            session_id,
            payload.question_id,
            existed.id,
        )
        return {
            "record": existed,
            "analysis": existed.ai_answer,
            "reference_answer": q.reference_answer,
            "grading_reused": True,
        }

    grading = call_doubao_grade(question_stem=q.stem, user_answer=payload.user_answer)
    record = PracticeRecord(
        session_id=session_id,
        question_id=payload.question_id,
        user_answer=payload.user_answer,
        ai_answer=grading["analysis"],
        ai_score=grading["score"],
    )
    db.add(record)
    db.flush()

    update_wrongbook_after_attempt(db, payload.question_id, int(grading["score"]))
    _update_mastery_by_formula(q, grading["score"])

    _finalize_session_if_done(db, session)

    db.commit()
    db.refresh(record)
    _try_session_summary_after_complete(db, session_id)
    return {
        "record": record,
        "analysis": grading["analysis"],
        "reference_answer": q.reference_answer,
        "grading_reused": False,
    }


@router.post("/daily/submit", response_model=PracticeSubmitResponse)
def submit_daily_answer(payload: PracticeSubmitRequest, db: Session = Depends(get_db)):
    q = db.get(Question, payload.question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    if settings.practice_daily_idempotency_enabled:
        window_s = max(1, int(settings.practice_daily_idempotency_seconds))
        cutoff = datetime.utcnow() - timedelta(seconds=window_s)
        recent = db.scalar(
            select(PracticeRecord)
            .where(
                PracticeRecord.session_id.is_(None),
                PracticeRecord.question_id == payload.question_id,
                PracticeRecord.user_answer == payload.user_answer,
                PracticeRecord.created_at >= cutoff,
            )
            .order_by(PracticeRecord.id.desc())
        )
        if recent is not None:
            logger.info(
                "daily_submit skip_ai reason=idempotent_window question_id=%s record_id=%s window_s=%s",
                payload.question_id,
                recent.id,
                window_s,
            )
            return {
                "record": recent,
                "analysis": recent.ai_answer,
                "reference_answer": q.reference_answer,
                "grading_reused": True,
            }

    grading = call_doubao_grade(question_stem=q.stem, user_answer=payload.user_answer)
    record = PracticeRecord(
        session_id=None,
        question_id=payload.question_id,
        user_answer=payload.user_answer,
        ai_answer=grading["analysis"],
        ai_score=grading["score"],
    )
    db.add(record)
    db.flush()

    update_wrongbook_after_attempt(db, payload.question_id, int(grading["score"]))
    _update_mastery_by_formula(q, grading["score"])

    db.commit()
    db.refresh(record)
    return {
        "record": record,
        "analysis": grading["analysis"],
        "reference_answer": q.reference_answer,
        "grading_reused": False,
    }


@router.post("/sessions/{session_id}/skip", response_model=PracticeSubmitResponse)
def skip_answer(session_id: int, payload: PracticeSkipRequest, db: Session = Depends(get_db)):
    session = db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")
    q = db.get(Question, payload.question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    existed = db.scalar(
        select(PracticeRecord).where(
            PracticeRecord.session_id == session_id,
            PracticeRecord.question_id == payload.question_id,
        )
    )
    if existed:
        logger.info(
            "practice_skip skip_duplicate session_id=%s question_id=%s record_id=%s",
            session_id,
            payload.question_id,
            existed.id,
        )
        return {
            "record": existed,
            "analysis": existed.ai_answer,
            "reference_answer": q.reference_answer,
            "grading_reused": True,
        }

    analysis = "未作答，记 0 分。建议先回忆核心要点后再复习参考答案。"
    record = PracticeRecord(
        session_id=session_id,
        question_id=payload.question_id,
        user_answer="",
        ai_answer=analysis,
        ai_score=0,
    )
    db.add(record)
    db.flush()

    update_wrongbook_after_attempt(db, payload.question_id, 0)
    _update_mastery_by_formula(q, 0)

    _finalize_session_if_done(db, session)

    db.commit()
    db.refresh(record)
    _try_session_summary_after_complete(db, session_id)
    return {
        "record": record,
        "analysis": analysis,
        "reference_answer": q.reference_answer,
        "grading_reused": False,
    }


@router.get("/wrongbook", response_model=WrongbookPageOut)
def list_wrongbook(
    state: str = Query("in", description="in: currently wrong; out: cleared; all: ever entered wrongbook"),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if state not in ("in", "out", "all"):
        raise HTTPException(status_code=400, detail="state must be in, out, or all")
    filters = []
    if category and category.strip():
        filters.append(Question.category == category.strip())
    if state == "in":
        filters.append(Question.wrongbook_active.is_(True))
    elif state == "out":
        filters.append(Question.wrongbook_active.is_(False))
        filters.append(Question.wrongbook_cleared_at.isnot(None))
    else:
        filters.append(Question.wrongbook_entered_at.isnot(None))

    count_stmt = select(func.count(Question.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int(db.scalar(count_stmt) or 0)

    stmt = select(Question)
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.order_by(Question.id.desc())
    offset = (page - 1) * page_size
    items = db.scalars(stmt.offset(offset).limit(page_size)).all()
    return WrongbookPageOut(total=total, page=page, page_size=page_size, items=items)


@router.post("/wrongbook/manual", response_model=QuestionOut)
def wrongbook_manual_add(payload: WrongbookManualAddRequest, db: Session = Depends(get_db)):
    q = db.get(Question, payload.question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    manual_add_to_wrongbook(db, q)
    db.commit()
    db.refresh(q)
    return q


@router.get("/sessions/{session_id}/summary", response_model=PracticeSessionSummaryResponse)
def practice_session_summary(session_id: int, db: Session = Depends(get_db)):
    session = db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")
    records = db.scalars(select(PracticeRecord).where(PracticeRecord.session_id == session_id)).all()
    total_score = int(sum(r.ai_score for r in records))
    if len(records) >= session.question_count and session.completed_at is None:
        session.total_score = total_score
        session.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(session)

    feedback = parse_stored_feedback(session)
    if session.completed_at and not session.summary_done:
        try:
            feedback = generate_session_summary_if_needed(db, session)
            db.commit()
            db.refresh(session)
        except Exception:
            db.rollback()
            logger.exception("session_summary on GET failed session_id=%s", session_id)
        session = db.get(PracticeSession, session_id)
        if session:
            feedback = parse_stored_feedback(session)

    summary_pending = bool(session and session.completed_at and not session.summary_done)
    return {
        "session_id": session_id,
        "total_score": total_score,
        "record_ids": [r.id for r in records],
        "completed_at": session.completed_at if session else None,
        "question_count": session.question_count if session else 0,
        "feedback": feedback,
        "summary_pending": summary_pending,
    }


@router.get("/sessions", response_model=list[PracticeSessionOut])
def list_practice_sessions(db: Session = Depends(get_db)):
    stmt = select(PracticeSession).where(PracticeSession.completed_at.is_not(None)).order_by(PracticeSession.id.desc())
    return db.scalars(stmt).all()


@router.get("/sessions/{session_id}/records")
def list_session_records(session_id: int, db: Session = Depends(get_db)):
    session = db.get(PracticeSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")
    records = db.scalars(
        select(PracticeRecord).where(PracticeRecord.session_id == session_id).order_by(PracticeRecord.id.asc())
    ).all()
    return {
        "session_id": session_id,
        "total_score": session.total_score,
        "completed_at": session.completed_at,
        "question_count": session.question_count,
        "records": records,
    }

