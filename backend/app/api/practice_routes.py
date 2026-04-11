from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
import zoneinfo

from app.core.database import get_db
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
)
from app.services.ai_service import call_doubao_grade

router = APIRouter(prefix="/api/practice", tags=["practice"])

try:
    _ACTIVITY_TZ = zoneinfo.ZoneInfo("Asia/Shanghai")
except zoneinfo.ZoneInfoNotFoundError:
    _ACTIVITY_TZ = timezone(timedelta(hours=8))
_NUM_WEEKS = 53


def _naive_dt_to_shanghai_date(dt: datetime) -> date:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_ACTIVITY_TZ).date()


def _shanghai_calendar_day_to_utc_naive_bounds(d: date) -> tuple[datetime, datetime]:
    """Inclusive start / exclusive end in naive UTC for rows stored as UTC wall times."""
    lower = (
        datetime.combine(d, datetime.min.time(), tzinfo=_ACTIVITY_TZ)
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )
    upper = (
        datetime.combine(d + timedelta(days=1), datetime.min.time(), tzinfo=_ACTIVITY_TZ)
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )
    return lower, upper


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
    Dense last-53-week window (371 days), Sunday-first columns, dates in Asia/Shanghai.
    Count = number of **practice_records rows** that calendar day (each submit / skip / daily
    creates one row). Same question answered multiple times counts multiple times.
    """
    today = datetime.now(_ACTIVITY_TZ).date()
    end_sunday = _sunday_start_of_week(today)
    start_sunday = end_sunday - timedelta(weeks=_NUM_WEEKS - 1)
    end_last = start_sunday + timedelta(days=_NUM_WEEKS * 7 - 1)

    lower_naive = (
        datetime.combine(start_sunday, datetime.min.time(), tzinfo=_ACTIVITY_TZ)
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )
    upper_exclusive_naive = (
        datetime.combine(end_last + timedelta(days=1), datetime.min.time(), tzinfo=_ACTIVITY_TZ)
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )

    rows = db.scalars(
        select(PracticeRecord.created_at).where(
            PracticeRecord.created_at >= lower_naive,
            PracticeRecord.created_at < upper_exclusive_naive,
        )
    ).all()

    per_day: Counter[date] = Counter()
    for ts in rows:
        per_day[_naive_dt_to_shanghai_date(ts)] += 1

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
        timezone="Asia/Shanghai",
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
        description="Filter to calendar day in Asia/Shanghai (YYYY-MM-DD); matches heatmap bucketing",
    ),
    db: Session = Depends(get_db),
):
    """
    Paginated log of every practice row (session submit/skip, daily submit).
    Use `shanghai_date` to reconcile counts with GET /api/practice/activity for that day.
    """
    bounds: tuple[datetime, datetime] | None = None
    if shanghai_date is not None and shanghai_date.strip():
        try:
            d = date.fromisoformat(shanghai_date.strip())
        except ValueError:
            raise HTTPException(status_code=400, detail="shanghai_date must be YYYY-MM-DD") from None
        bounds = _shanghai_calendar_day_to_utc_naive_bounds(d)

    base_filter = []
    if bounds is not None:
        lo, hi = bounds
        base_filter = [PracticeRecord.created_at >= lo, PracticeRecord.created_at < hi]

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


@router.get("/ping")
def practice_ping() -> dict:
    return {"message": "practice module ready"}


@router.post("/sessions/start", response_model=PracticeSessionStartResponse)
def start_practice_session(
    category: str | None = None,
    count: int = Query(10, description="Number of questions: 5, 10, or 15"),
    db: Session = Depends(get_db),
):
    if count not in ALLOWED_SESSION_SIZES:
        raise HTTPException(status_code=400, detail="count must be 5, 10, or 15")
    stmt = select(Question)
    if category:
        stmt = stmt.where(Question.category == category)
    questions = db.scalars(stmt.order_by(func.rand()).limit(count)).all()
    if len(questions) < count:
        scope = f"Category '{category}'" if category else "Question bank (all categories)"
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
def list_practice_categories(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Question.category, func.count(Question.id))
        .group_by(Question.category)
        .order_by(Question.category.asc())
    ).all()
    total_all = int(db.scalar(select(func.count()).select_from(Question)) or 0)
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
        raise HTTPException(status_code=409, detail="This question already submitted in current session")

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

    _update_mastery_by_formula(q, grading["score"])

    _finalize_session_if_done(db, session)

    db.commit()
    db.refresh(record)
    return {"record": record, "analysis": grading["analysis"], "reference_answer": q.reference_answer}


@router.post("/daily/submit", response_model=PracticeSubmitResponse)
def submit_daily_answer(payload: PracticeSubmitRequest, db: Session = Depends(get_db)):
    q = db.get(Question, payload.question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

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

    _update_mastery_by_formula(q, grading["score"])

    db.commit()
    db.refresh(record)
    return {"record": record, "analysis": grading["analysis"], "reference_answer": q.reference_answer}


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
        raise HTTPException(status_code=409, detail="This question already submitted in current session")

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

    _update_mastery_by_formula(q, 0)

    _finalize_session_if_done(db, session)

    db.commit()
    db.refresh(record)
    return {"record": record, "analysis": analysis, "reference_answer": q.reference_answer}


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
    return {
        "session_id": session_id,
        "total_score": total_score,
        "record_ids": [r.id for r in records],
        "completed_at": session.completed_at,
        "question_count": session.question_count,
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

