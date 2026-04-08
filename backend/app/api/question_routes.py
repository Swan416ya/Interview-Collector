from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.question import Question
from app.schemas.question import QuestionCreate, QuestionOut

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=list[QuestionOut])
def list_questions(db: Session = Depends(get_db)):
    return db.scalars(select(Question).order_by(Question.id.desc())).all()


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

