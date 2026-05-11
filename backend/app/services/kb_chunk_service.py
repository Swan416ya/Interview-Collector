"""Sync question text into document_chunks and keyword search (SQLite LIKE / MySQL FULLTEXT + LIKE fallback)."""

from __future__ import annotations

import logging
import re

from sqlalchemy import delete, or_, select, text
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.models.question import Question

logger = logging.getLogger(__name__)

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


def _latin_keywords(q: str) -> list[str]:
    """English / tech tokens (Redis, TCP, MySQL) for queries like「Redis是干什么用的」with no spaces."""
    seen: set[str] = set()
    out: list[str] = []
    for m in re.finditer(r"[A-Za-z][A-Za-z0-9_-]*", q):
        w = m.group(0)
        if len(w) < 2:
            continue
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            out.append(w)
    return out[:12]


def _shorter_prefixes(q: str) -> list[str]:
    """When the whole line is not a substring of any chunk, try leading runs (CJK questions)."""
    q = q.strip()
    if len(q) < 4:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for n in (16, 12, 8, 6, 4):
        if n >= len(q) or n < 2:
            continue
        sub = q[:n]
        if sub not in seen:
            seen.add(sub)
            out.append(sub)
    return out


def search_chunks(db: Session, query: str, top_k: int = 5) -> list[DocumentChunk]:
    """Return up to top_k chunks most relevant to query (best-effort; CJK-friendly via substring match)."""
    q = (query or "").strip()
    if not q or top_k <= 0:
        return []

    bind = db.get_bind()
    dialect = bind.dialect.name if bind is not None else "sqlite"

    if dialect == "mysql":
        try:
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
        except Exception:
            logger.warning("document_chunks FULLTEXT failed, falling back to substring search", exc_info=True)

    # SQLite, empty FT on MySQL, or FT error: substring search
    stmt = select(DocumentChunk)
    tokens = _tokenize_query(q)
    if not tokens:
        tokens = [q]
    # AND: every whitespace-separated token must appear (strict; may miss when terms split across stem/ref)
    for t in tokens[:8]:
        stmt = stmt.where(DocumentChunk.text.contains(t, autoescape=True))
    found = list(db.scalars(stmt.limit(top_k)).all())
    if found:
        return found

    # Latin / API 名等：整句无法子串命中时仍可用「Redis」命中题干
    latins = _latin_keywords(q)
    if latins:
        or_lat = or_(*[DocumentChunk.text.contains(w, autoescape=True) for w in latins])
        found = list(db.scalars(select(DocumentChunk).where(or_lat).limit(top_k)).all())
        if found:
            return found

    # 无空格长中文：整句少见，试较短前缀
    if len(tokens) == 1 and len(q) >= 4:
        for sub in _shorter_prefixes(q):
            found = list(
                db.scalars(
                    select(DocumentChunk).where(DocumentChunk.text.contains(sub, autoescape=True)).limit(top_k)
                ).all()
            )
            if found:
                return found

    # OR: any token matches (better recall for e.g. "Redis 持久化" vs stem-only + ref-only)
    if len(tokens) > 1:
        or_cond = or_(*[DocumentChunk.text.contains(t, autoescape=True) for t in tokens[:8]])
        found = list(db.scalars(select(DocumentChunk).where(or_cond).limit(top_k)).all())
        if found:
            return found
        stmt2 = select(DocumentChunk).where(DocumentChunk.text.contains(q[:500], autoescape=True)).limit(top_k)
        return list(db.scalars(stmt2).all())
    return []


def reindex_all_questions(db: Session) -> int:
    """Sync chunks for every question; returns number of questions processed. Caller should commit."""
    rows = db.scalars(select(Question)).all()
    for question in rows:
        sync_question_chunks(db, question)
    return len(rows)
