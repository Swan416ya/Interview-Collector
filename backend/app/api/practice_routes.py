from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.question import PracticeRecord, PracticeSession, Question
from app.schemas.practice import (
    PracticeSessionOut,
    PracticeSessionStartResponse,
    PracticeSessionSummaryResponse,
    PracticeSubmitResponse,
    PracticeSubmitRequest,
)
from app.services.ai_service import call_doubao_grade

router = APIRouter(prefix="/api/practice", tags=["practice"])


@router.get("/ping")
def practice_ping() -> dict:
    return {"message": "practice module ready"}


@router.post("/sessions/start", response_model=PracticeSessionStartResponse)
def start_practice_session(db: Session = Depends(get_db)):
    questions = db.scalars(select(Question).order_by(func.rand()).limit(10)).all()
    if len(questions) < 10:
        raise HTTPException(status_code=400, detail="Need at least 10 questions in the question bank")
    session = PracticeSession(total_score=0)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "questions": questions}


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

    # Mastery remains 0-100 in question bank page; convert 10-point score to percentage.
    avg_score = db.scalar(select(func.avg(PracticeRecord.ai_score)).where(PracticeRecord.question_id == q.id))
    q.mastery_score = int(round(float(avg_score or 0) * 10))

    session_scores = db.scalars(select(PracticeRecord.ai_score).where(PracticeRecord.session_id == session_id)).all()
    if len(session_scores) >= 10:
        session.total_score = int(sum(session_scores))
        session.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(record)
    return {"record": record, "analysis": grading["analysis"], "reference_answer": q.reference_answer}


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

