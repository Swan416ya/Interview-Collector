from pydantic import BaseModel, Field


class KbQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class KbCitation(BaseModel):
    chunk_id: int
    question_id: int
    excerpt: str
    source_type: str


class KbQueryResponse(BaseModel):
    answer: str
    citations: list[KbCitation]


class KbReindexResponse(BaseModel):
    questions_processed: int
