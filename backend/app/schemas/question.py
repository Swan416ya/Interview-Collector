from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestionCreate(BaseModel):
    stem: str = Field(min_length=3)
    category: str = "未分类"
    difficulty: int = Field(default=3, ge=1, le=5)
    reference_answer: str | None = Field(
        default=None,
        max_length=50000,
        description="若传入非空字符串，则直接使用为参考答案，不调用 AI 生成",
    )


class QuestionUpdate(BaseModel):
    stem: str = Field(min_length=3)
    category: str = "未分类"
    difficulty: int = Field(default=3, ge=1, le=5)


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stem: str
    category: str
    difficulty: int
    reference_answer: str
    mastery_score: int
    created_at: datetime


class QuestionPageOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[QuestionOut]


class PracticeRecordCreate(BaseModel):
    session_id: int | None = None
    user_answer: str = ""
    ai_answer: str = ""
    ai_score: int = Field(default=0, ge=0, le=10)


class PracticeRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int | None
    question_id: int
    user_answer: str
    ai_answer: str
    ai_score: int
    created_at: datetime

