from pydantic import BaseModel, ConfigDict, Field


class QuestionCreate(BaseModel):
    stem: str = Field(min_length=3)
    category: str = "未分类"
    difficulty: int = Field(default=3, ge=1, le=5)


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stem: str
    category: str
    difficulty: int

