from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.kb import KbCitation, KbQueryRequest, KbQueryResponse, KbReindexResponse
from app.services.ai_service import call_doubao_kb_query
from app.services.kb_chunk_service import reindex_all_questions, search_chunks

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])

KB_NOT_FOUND = "知识库中未找到相关条目"


def _excerpt(text: str, max_len: int = 240) -> str:
    t = (text or "").replace("\r\n", "\n").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


@router.post("/query", response_model=KbQueryResponse)
def kb_query(payload: KbQueryRequest, db: Session = Depends(get_db)):
    q = payload.query.strip()
    chunks = search_chunks(db, q, top_k=payload.top_k)
    if not chunks:
        return KbQueryResponse(answer=KB_NOT_FOUND, citations=[])

    fragments = [
        {
            "chunk_id": c.id,
            "question_id": c.question_id,
            "source_type": c.source_type,
            "text": c.text,
        }
        for c in chunks
    ]
    allowed_ids = {c.id for c in chunks}
    raw = call_doubao_kb_query(q, fragments)
    answer = str(raw.get("answer", "")).strip() or KB_NOT_FOUND

    cited_ids: list[int] = []
    raw_ids = raw.get("cited_chunk_ids")
    if isinstance(raw_ids, list):
        for x in raw_ids:
            if isinstance(x, int) and x in allowed_ids:
                cited_ids.append(x)
            elif isinstance(x, str) and x.isdigit():
                xi = int(x)
                if xi in allowed_ids:
                    cited_ids.append(xi)

    if answer != KB_NOT_FOUND and not cited_ids:
        cited_ids = [c.id for c in chunks]

    by_id = {c.id: c for c in chunks}
    citations: list[KbCitation] = []
    seen: set[int] = set()
    for cid in cited_ids:
        if cid in seen or cid not in by_id:
            continue
        seen.add(cid)
        c = by_id[cid]
        citations.append(
            KbCitation(
                chunk_id=c.id,
                question_id=c.question_id,
                excerpt=_excerpt(c.text),
                source_type=c.source_type,
            )
        )
    return KbQueryResponse(answer=answer, citations=citations)


@router.post("/reindex", response_model=KbReindexResponse)
def kb_reindex(db: Session = Depends(get_db)):
    n = reindex_all_questions(db)
    db.commit()
    return KbReindexResponse(questions_processed=n)
