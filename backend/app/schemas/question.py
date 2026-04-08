from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestionCreate(BaseModel):
    stem: str = Field(min_length=3)
    category: str = "未分类"
    difficulty: int = Field(default=3, ge=1, le=5)


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
    mastery_score: int
    created_at: datetime


class PracticeRecordCreate(BaseModel):
    user_answer: str = ""
    ai_answer: str = ""
    ai_score: int = Field(default=0, ge=0, le=100)


class PracticeRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    user_answer: str
    ai_answer: str
    ai_score: int
    created_at: datetime

