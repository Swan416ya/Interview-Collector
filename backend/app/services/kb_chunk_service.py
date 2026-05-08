"""Sync question text into document_chunks and keyword search (SQLite LIKE / MySQL FULLTEXT + LIKE fallback)."""

from __future__ import annotations

import re

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.models.question import Question

CHUNK_SOURCE_QUESTION_STEM = "question_stem"
CHUNK_SOURCE_QUESTION_REFERENCE = "question_reference"


def sync_question_chunks(db: Session, question: Question) -> None:
    """Replace all chunks for this question with stem + optional reference rows."""
    db.execute(delete(DocumentChunk).where(DocumentChunk.question_id == question.id))
    stem = (question.stem or "").strip()
    if stem:
        db.add(
            DocumentChunk(
                question_id=question.id,
                source_type=CHUNK_SOURCE_QUESTION_STEM,
                chunk_index=0,
                text=stem,
                chunk_meta=None,
            )
        )
    ref = (question.reference_answer or "").strip()
    if ref:
        db.add(
            DocumentChunk(
                question_id=question.id,
                source_type=CHUNK_SOURCE_QUESTION_REFERENCE,
                chunk_index=1,
                text=ref,
                chunk_meta=None,
            )
        )


def _tokenize_query(q: str) -> list[str]:
    parts = re.split(r"\s+", q.strip())
    return [p for p in parts if p]


def search_chunks(db: Session, query: str, top_k: int = 5) -> list[DocumentChunk]:
    """Return up to top_k chunks most relevant to query (best-effort; CJK-friendly via substring match)."""
    q = (query or "").strip()
    if not q or top_k <= 0:
        return []

    bind = db.get_bind()
    dialect = bind.dialect.name if bind is not None else "sqlite"

    if dialect == "mysql":
        rows = db.execute(
            text(
                """
                SELECT id FROM document_chunks
                WHERE MATCH(`text`) AGAINST (:q IN NATURAL LANGUAGE MODE)
                LIMIT :lim
                """
            ),
            {"q": q, "lim": top_k},
        ).fetchall()
        ids = [int(r[0]) for r in rows if r and r[0] is not None]
        if ids:
            by_id = {c.id: c for c in db.scalars(select(DocumentChunk).where(DocumentChunk.id.in_(ids))).all()}
            return [by_id[i] for i in ids if i in by_id]

    # SQLite, empty FT on MySQL, or short Chinese: LIKE / contains
    stmt = select(DocumentChunk)
    tokens = _tokenize_query(q)
    if not tokens:
        tokens = [q]
    for t in tokens[:8]:
        stmt = stmt.where(DocumentChunk.text.contains(t, autoescape=True))
    found = list(db.scalars(stmt.limit(top_k)).all())
    if found:
        return found

    # Last resort: whole string as one substring (helps single long CJK phrase on SQLite)
    if len(tokens) > 1:
        stmt2 = select(DocumentChunk).where(DocumentChunk.text.contains(q[:500], autoescape=True)).limit(top_k)
        return list(db.scalars(stmt2).all())
    return []


def reindex_all_questions(db: Session) -> int:
    """Sync chunks for every question; returns number of questions processed. Caller should commit."""
    rows = db.scalars(select(Question)).all()
    for question in rows:
        sync_question_chunks(db, question)
    return len(rows)
