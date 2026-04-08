from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.question import PracticeRecordOut, QuestionOut


class PracticeSessionStartResponse(BaseModel):
    session_id: int
    questions: list[QuestionOut]


class PracticeSessionCustomStartRequest(BaseModel):
    question_ids: list[int] = Field(min_length=10, max_length=10)


class PracticeCategoryOption(BaseModel):
    category: str
    total_questions: int
    selectable: bool


class PracticeSubmitRequest(BaseModel):
    question_id: int
    user_answer: str = Field(min_length=1)


class PracticeSkipRequest(BaseModel):
    question_id: int


class PracticeSubmitResponse(BaseModel):
    record: PracticeRecordOut
    analysis: str
    reference_answer: str


class PracticeSessionSummaryResponse(BaseModel):
    session_id: int
    total_score: int
    record_ids: list[int]
    completed_at: datetime | None


class PracticeSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_score: int
    completed_at: datetime | None
    created_at: datetime

