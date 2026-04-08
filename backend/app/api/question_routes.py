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
from app.services.ai_service import call_doubao_reference_answer

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=list[QuestionOut])
def list_questions(
    category: str | None = Query(default=None),
    difficulty: int | None = Query(default=None, ge=1, le=5),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db),
):
    stmt = select(Question)
    if category:
        stmt = stmt.where(Question.category == category.strip())
    if difficulty is not None:
        stmt = stmt.where(Question.difficulty == difficulty)

    order_desc = sort_order.lower() != "asc"
    if sort_by == "mastery_score":
        stmt = stmt.order_by(Question.mastery_score.desc() if order_desc else Question.mastery_score.asc())
    else:
        stmt = stmt.order_by(Question.created_at.desc() if order_desc else Question.created_at.asc())
    return db.scalars(stmt).all()


@router.post("", response_model=QuestionOut)
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)):
    reference_answer = call_doubao_reference_answer(payload.stem)
    item = Question(
        stem=payload.stem,
        category=payload.category,
        difficulty=payload.difficulty,
        reference_answer=reference_answer,
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
        session_id=payload.session_id,
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
    q.mastery_score = int(round(float(avg_score or 0) * 10))

    db.commit()
    db.refresh(record)
    return record


@router.post("/backfill-reference-answers")
def backfill_reference_answers(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    candidates = db.scalars(
        select(Question).where((Question.reference_answer.is_(None)) | (Question.reference_answer == "")).limit(limit)
    ).all()
    updated = 0
    failed: list[dict] = []
    for q in candidates:
        try:
            q.reference_answer = call_doubao_reference_answer(q.stem)
            updated += 1
        except Exception as exc:  # noqa: BLE001
            failed.append({"question_id": q.id, "error": str(exc)})
    db.commit()
    return {"scanned": len(candidates), "updated": updated, "failed": failed}

