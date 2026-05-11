"""Generate and persist one LLM session summary when a practice session completes."""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.question import PracticeRecord, PracticeSession, Question
from app.schemas.practice import SessionFeedbackOut
from app.services.ai_service import call_doubao_session_summary

logger = logging.getLogger(__name__)


def _preview_answer(text: str, max_len: int = 140) -> str:
    t = (text or "").replace("\r\n", "\n").replace("\n", " ").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _normalize_dimensions(raw_list: list) -> list[dict]:
    out: list[dict] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip() or "dim"
        label = str(item.get("label", "")).strip() or key
        try:
            score = int(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(10, score))
        out.append({"key": key, "label": label, "score": score})
    return out


def _coerce_feedback_dict(raw: dict) -> dict:
    """Tolerate slightly malformed model output before Pydantic."""
    summary_text = str(raw.get("summary_text", "")).strip()
    dims_in = raw.get("dimensions")
    if not isinstance(dims_in, list):
        dims_in = []
    dims = _normalize_dimensions(dims_in)
    # Pad or trim to exactly 5 for radar UI
    default_labels = [
        ("correctness", "正确性"),
        ("completeness", "完整性"),
        ("articulation", "表达力"),
        ("depth", "知识深度"),
        ("consistency", "稳定性"),
    ]
    while len(dims) < 5:
        k, lab = default_labels[len(dims)]
        dims.append({"key": k, "label": lab, "score": 5})
    dims = dims[:5]
    return {"summary_text": summary_text, "dimensions": dims}


def build_session_digest(session: PracticeSession, records: list[PracticeRecord], qmap: dict[int, Question]) -> str:
    lines: list[str] = []
    lines.append(f"本轮共 {session.question_count} 题，总分 {session.total_score}（满分 {session.question_count * 10}）。")
    lines.append("逐题摘要：")
    for i, rec in enumerate(records, start=1):
        q = qmap.get(rec.question_id)
        stem = (q.stem if q else "（题目已删除）").strip()
        stem_short = stem[:280] + ("…" if len(stem) > 280 else "")
        lines.append(
            f"\n【第{i}题】得分 {rec.ai_score}/10\n题干：{stem_short}\n作答摘要：{_preview_answer(rec.user_answer)}\n"
            f"阅卷解析摘要：{_preview_answer(rec.ai_answer, 160)}"
        )
    return "\n".join(lines)


def generate_session_summary_if_needed(db: Session, session: PracticeSession) -> SessionFeedbackOut | None:
    """
    If session is complete and summary not yet stored, call LLM and persist JSON.
    Returns validated feedback on success; None if skipped or on failure (logged).
    """
    if session.summary_done and session.session_feedback_json:
        try:
            return SessionFeedbackOut.model_validate(json.loads(session.session_feedback_json))
        except (json.JSONDecodeError, ValidationError):
            pass

    if not session.completed_at:
        return None

    records = db.scalars(
        select(PracticeRecord).where(PracticeRecord.session_id == session.id).order_by(PracticeRecord.id.asc())
    ).all()
    if len(records) < session.question_count:
        return None

    qids = list({r.question_id for r in records})
    questions = db.scalars(select(Question).where(Question.id.in_(qids))).all()
    qmap = {q.id: q for q in questions}

    digest = build_session_digest(session, records, qmap)
    try:
        raw = call_doubao_session_summary(digest)
    except Exception:
        logger.exception("session_summary LLM failed session_id=%s", session.id)
        return None

    try:
        coerced = _coerce_feedback_dict(raw if isinstance(raw, dict) else {})
        feedback = SessionFeedbackOut.model_validate(coerced)
    except ValidationError:
        logger.exception("session_summary validate failed session_id=%s raw=%s", session.id, raw)
        return None

    session.session_feedback_json = json.dumps(feedback.model_dump(), ensure_ascii=False)
    session.summary_done = True
    return feedback


def parse_stored_feedback(session: PracticeSession) -> SessionFeedbackOut | None:
    if not session.session_feedback_json:
        return None
    try:
        return SessionFeedbackOut.model_validate(json.loads(session.session_feedback_json))
    except (json.JSONDecodeError, ValidationError):
        return None
