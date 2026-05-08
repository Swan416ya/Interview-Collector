from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.question import PracticeRecordOut, QuestionOut

ALLOWED_SESSION_SIZES = frozenset({5, 10, 15})


class PracticeSessionStartResponse(BaseModel):
    session_id: int
    questions: list[QuestionOut]
    question_count: int


class PracticeSessionCustomStartRequest(BaseModel):
    question_ids: list[int]

    @field_validator("question_ids")
    @classmethod
    def length_and_unique(cls, v: list[int]) -> list[int]:
        n = len(v)
        if n not in ALLOWED_SESSION_SIZES:
            raise ValueError("question_ids length must be 5, 10, or 15")
        if len(set(v)) != n:
            raise ValueError("question_ids must be unique")
        return v


class PracticeCategoryOption(BaseModel):
    category: str
    total_questions: int
    selectable: bool


class PracticeCategoriesResponse(BaseModel):
    categories: list[PracticeCategoryOption]
    total_questions_all: int


class PracticeSubmitRequest(BaseModel):
    question_id: int
    user_answer: str = Field(min_length=1)


class PracticeSkipRequest(BaseModel):
    question_id: int


class PracticeSubmitResponse(BaseModel):
    record: PracticeRecordOut
    analysis: str
    reference_answer: str
    grading_reused: bool = Field(
        default=False,
        description="True when daily submit returned a recent identical submission without calling the grader again",
    )


class PracticeSessionSummaryResponse(BaseModel):
    session_id: int
    total_score: int
    record_ids: list[int]
    completed_at: datetime | None
    question_count: int


class PracticeSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_score: int
    question_count: int
    completed_at: datetime | None
    created_at: datetime


class PracticeActivityDayOut(BaseModel):
    """One calendar day in the heatmap window (Asia/Shanghai)."""

    date: str
    count: int
    level: int = Field(ge=0, le=4, description="0=empty, 1-4 green intensity by count tiers")


class PracticeActivityResponse(BaseModel):
    timezone: str = Field(
        description="How day keys are derived: storage calendar date of created_at (SQL date(created_at)), not UTC→Shanghai conversion",
    )
    start_date: str
    end_date: str
    today: str
    total_questions: int
    active_days: int
    days: list[PracticeActivityDayOut]


class PracticeRecordFeedItem(BaseModel):
    """Single row for global answer log (joins question stem)."""

    id: int
    session_id: int | None
    question_id: int
    question_stem: str
    user_answer: str
    ai_score: int
    created_at: datetime


class PracticeRecordFeedPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PracticeRecordFeedItem]

