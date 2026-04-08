from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.question import PracticeRecord, Question
from app.schemas.question import (
    PracticeRecordCreate,
    PracticeRecordOut,
    QuestionCreate,
    QuestionOut,
    QuestionUpdate,
)

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=list[QuestionOut])
def list_questions(
    category: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    difficulty: int | None = Query(default=None, ge=1, le=5),
    db: Session = Depends(get_db),
):
    stmt = select(Question)
    if category:
        stmt = stmt.where(Question.category == category.strip())
    if difficulty is not None:
        stmt = stmt.where(Question.difficulty == difficulty)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(Question.stem.like(like))
    stmt = stmt.order_by(Question.id.desc())
    return db.scalars(stmt).all()


@router.post("", response_model=QuestionOut)
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)):
    item = Question(
        stem=payload.stem,
        category=payload.category,
        difficulty=payload.difficulty,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{question_id}", response_model=QuestionOut)
def update_question(question_id: int, payload: QuestionUpdate, db: Session = Depends(get_db)):
    item = db.get(Question, question_id)
    if not item:
        raise HTTPException(status_code=404, detail="Question not found")
    item.stem = payload.stem
    item.category = payload.category
    item.difficulty = payload.difficulty
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):
    item = db.get(Question, question_id)
    if not item:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}


@router.get("/{question_id}/records", response_model=list[PracticeRecordOut])
def list_question_records(question_id: int, db: Session = Depends(get_db)):
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    stmt = select(PracticeRecord).where(PracticeRecord.question_id == question_id).order_by(PracticeRecord.id.desc())
    return db.scalars(stmt).all()


@router.post("/{question_id}/records", response_model=PracticeRecordOut)
def create_question_record(question_id: int, payload: PracticeRecordCreate, db: Session = Depends(get_db)):
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    record = PracticeRecord(
        question_id=question_id,
        user_answer=payload.user_answer,
        ai_answer=payload.ai_answer,
        ai_score=payload.ai_score,
    )
    db.add(record)
    db.flush()

    avg_score = db.scalar(
        select(func.avg(PracticeRecord.ai_score)).where(PracticeRecord.question_id == question_id)
    )
    q.mastery_score = int(round(float(avg_score or 0)))

    db.commit()
    db.refresh(record)
    return record

