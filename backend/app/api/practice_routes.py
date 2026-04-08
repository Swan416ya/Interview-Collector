from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.question import PracticeRecord, PracticeSession, Question
from app.schemas.practice import (
    PracticeSkipRequest,
    PracticeCategoryOption,
    PracticeSessionCustomStartRequest,
    PracticeSessionOut,
    PracticeSessionStartResponse,
    PracticeSessionSummaryResponse,
    PracticeSubmitResponse,
    PracticeSubmitRequest,
)
from app.services.ai_service import call_doubao_grade

router = APIRouter(prefix="/api/practice", tags=["practice"])


def _update_mastery_by_formula(question: Question, latest_score_0_10: int) -> None:
    old_mastery = int(question.mastery_score or 0)
    latest_score_100 = max(0, min(10, latest_score_0_10)) * 10
    new_mastery = round(old_mastery * 0.7 + latest_score_100 * 0.3)
    question.mastery_score = max(0, min(100, int(new_mastery)))


@router.get("/ping")
def practice_ping() -> dict:
    return {"message": "practice module ready"}


@router.post("/sessions/start", response_model=PracticeSessionStartResponse)
def start_practice_session(category: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Question)
    if category:
        stmt = stmt.where(Question.category == category)
    questions = db.scalars(stmt.order_by(func.rand()).limit(10)).all()
    if len(questions) < 10:
        if category:
            raise HTTPException(status_code=400, detail=f"Category '{category}' has less than 10 questions")
        raise HTTPException(status_code=400, detail="Need at least 10 questions in the question bank")
    session = PracticeSession(total_score=0)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "questions": questions}


@router.post("/sessions/start/custom", response_model=PracticeSessionStartResponse)
def start_practice_session_custom(payload: PracticeSessionCustomStartRequest, db: Session = Depends(get_db)):
    unique_ids = list(dict.fromkeys(payload.question_ids))
    if len(unique_ids) != 10:
        raise HTTPException(status_code=400, detail="question_ids must contain 10 unique question ids")

    questions = db.scalars(select(Question).where(Question.id.in_(unique_ids))).all()
    if len(questions) != 10:
        raise HTTPException(status_code=400, detail="Some question ids do not exist")

    # Return in the incoming order so client can keep its planned sequence.
    question_map = {q.id: q for q in questions}
    ordered_questions = [question_map[qid] for qid in unique_ids if qid in question_map]

    session = PracticeSession(total_score=0)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "questions": ordered_questions}


@router.get("/categories", response_model=list[PracticeCategoryOption])
def list_practice_categories(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Question.category, func.count(Question.id))
        .group_by(Question.category)
        .order_by(Question.category.asc())
    ).all()
    return [
        {
            "category": category or "未分类",
            "total_questions": int(total),
            "selectable": int(total) >= 10,
        }
        for category, total in rows
    ]


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

    session_scores = db.scalars(select(PracticeRecord.ai_score).where(PracticeRecord.session_id == session_id)).all()
    if len(session_scores) >= 10:
        session.total_score = int(sum(session_scores))
        session.completed_at = datetime.utcnow()

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

    session_scores = db.scalars(select(PracticeRecord.ai_score).where(PracticeRecord.session_id == session_id)).all()
    if len(session_scores) >= 10:
        session.total_score = int(sum(session_scores))
        session.completed_at = datetime.utcnow()

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
    if len(records) >= 10 and session.completed_at is None:
        session.total_score = total_score
        session.completed_at = datetime.utcnow()
        db.commit()
    return {
        "session_id": session_id,
        "total_score": total_score,
        "record_ids": [r.id for r in records],
        "completed_at": session.completed_at,
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
        "records": records,
    }

