from pydantic import BaseModel, Field


class ImportQuestionItem(BaseModel):
    stem: str = Field(min_length=3)
    category_name: str = Field(min_length=1, max_length=64)
    roles: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    difficulty: int = Field(default=3, ge=1, le=5)
    answer_reference: str | None = None


class ImportPayload(BaseModel):
    questions: list[ImportQuestionItem] = Field(default_factory=list)

