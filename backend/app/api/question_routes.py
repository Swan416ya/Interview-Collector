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
    QuestionPageOut,
    QuestionUpdate,
)
from app.services.ai_service import call_doubao_reference_answer
from app.services.reference_answer_resolver import resolve_reference_for_stem

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=list[QuestionOut])
def list_questions(
    category: str | None = Query(default=None),
    difficulty: int | None = Query(default=None, ge=1, le=5),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db),
):
    recent_subq = (
        select(
            PracticeRecord.question_id.label("qid"),
            func.max(PracticeRecord.created_at).label("last_seen"),
        )
        .group_by(PracticeRecord.question_id)
        .subquery()
    )
    stmt = select(Question).outerjoin(recent_subq, Question.id == recent_subq.c.qid)
    if category:
        stmt = stmt.where(Question.category == category.strip())
    if difficulty is not None:
        stmt = stmt.where(Question.difficulty == difficulty)

    order_desc = sort_order.lower() != "asc"
    if sort_by == "mastery_score":
        stmt = stmt.order_by(Question.mastery_score.desc() if order_desc else Question.mastery_score.asc())
    elif sort_by == "recent_encountered":
        stmt = stmt.order_by(
            recent_subq.c.last_seen.desc() if order_desc else recent_subq.c.last_seen.asc(),
            Question.created_at.desc(),
        )
    elif sort_by == "id":
        stmt = stmt.order_by(Question.id.desc() if order_desc else Question.id.asc())
    else:
        stmt = stmt.order_by(Question.created_at.desc() if order_desc else Question.created_at.asc())
    return db.scalars(stmt).all()


@router.get("/page", response_model=QuestionPageOut)
def list_questions_page(
    category: str | None = Query(default=None),
    difficulty: int | None = Query(default=None, ge=1, le=5),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    recent_subq = (
        select(
            PracticeRecord.question_id.label("qid"),
            func.max(PracticeRecord.created_at).label("last_seen"),
        )
        .group_by(PracticeRecord.question_id)
        .subquery()
    )
    base_stmt = select(Question).outerjoin(recent_subq, Question.id == recent_subq.c.qid)
    count_stmt = select(func.count(Question.id))
    if category:
        category_val = category.strip()
        base_stmt = base_stmt.where(Question.category == category_val)
        count_stmt = count_stmt.where(Question.category == category_val)
    if difficulty is not None:
        base_stmt = base_stmt.where(Question.difficulty == difficulty)
        count_stmt = count_stmt.where(Question.difficulty == difficulty)

    order_desc = sort_order.lower() != "asc"
    if sort_by == "mastery_score":
        base_stmt = base_stmt.order_by(Question.mastery_score.desc() if order_desc else Question.mastery_score.asc())
    elif sort_by == "recent_encountered":
        base_stmt = base_stmt.order_by(
            recent_subq.c.last_seen.desc() if order_desc else recent_subq.c.last_seen.asc(),
            Question.created_at.desc(),
        )
    elif sort_by == "id":
        base_stmt = base_stmt.order_by(Question.id.desc() if order_desc else Question.id.asc())
    else:
        base_stmt = base_stmt.order_by(Question.created_at.desc() if order_desc else Question.created_at.asc())

    total = int(db.scalar(count_stmt) or 0)
    offset = (page - 1) * page_size
    items = db.scalars(base_stmt.offset(offset).limit(page_size)).all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


def _update_mastery_by_formula(question: Question, latest_score_0_10: int) -> None:
    old_mastery = int(question.mastery_score or 0)
    latest_score_100 = max(0, min(10, latest_score_0_10)) * 10
    new_mastery = round(old_mastery * 0.7 + latest_score_100 * 0.3)
    question.mastery_score = max(0, min(100, int(new_mastery)))


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


@router.post("/{question_id}/refresh-reference", response_model=QuestionOut)
def refresh_question_reference_answer(question_id: int, db: Session = Depends(get_db)):
    item = db.get(Question, question_id)
    if not item:
        raise HTTPException(status_code=404, detail="Question not found")
    try:
        item.reference_answer = call_doubao_reference_answer(item.stem)
        db.commit()
        db.refresh(item)
        return item
    except Exception:
        db.rollback()
        raise


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

    _update_mastery_by_formula(q, payload.ai_score)

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
    reference_cache: dict[str, str] = {}
    for q in candidates:
        try:
            q.reference_answer = resolve_reference_for_stem(q.stem, batch_cache=reference_cache)
            updated += 1
        except Exception as exc:  # noqa: BLE001
            failed.append({"question_id": q.id, "error": str(exc)})
    db.commit()
    return {"scanned": len(candidates), "updated": updated, "failed": failed}

