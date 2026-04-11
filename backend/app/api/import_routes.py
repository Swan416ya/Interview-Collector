import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.question import Question
from app.models.taxonomy import Category, Company, QuestionCompany, QuestionRole, Role
from app.schemas.importing import (
    ImportCommitOneResponse,
    ImportPayload,
    ImportPreviewRequest,
    ImportQuestionItem,
)
from app.services.ai_service import call_doubao_extract, call_doubao_reference_answer

router = APIRouter(prefix="/api/import", tags=["import"])
logger = logging.getLogger(__name__)


def _fallback_category(category_names: set[str]) -> str:
    if "未分类" in category_names:
        return "未分类"
    return sorted(category_names)[0]


def _normalize_for_commit(
    item: ImportQuestionItem,
    category_names: set[str],
    role_by_name: dict[str, Role],
) -> tuple[str, list[str]]:
    """
    AI 偶尔会输出不在白名单里的 category/role。入库时收敛到合法值，避免 400。
    - 分类：不在库中则改为「未分类」（若存在），否则取字典序第一个分类。
    - 岗位：仅保留库中存在的名称；可退化为空列表（题目可无关联岗位）。
    """
    raw_cat = (item.category_name or "").strip()
    if raw_cat in category_names:
        cat = raw_cat
    else:
        cat = _fallback_category(category_names)
        logger.warning(
            "import commit: category %r not in DB, using %r (stem=%.80r)",
            raw_cat,
            cat,
            item.stem,
        )

    raw_roles = list(item.roles) if item.roles else []
    valid_roles = [r for r in raw_roles if r in role_by_name]
    dropped = [r for r in raw_roles if r not in role_by_name]
    if dropped:
        logger.warning(
            "import commit: dropped invalid roles %r (stem=%.80r)",
            dropped,
            item.stem,
        )
    return cat, valid_roles


def _load_taxonomy(db: Session) -> tuple[set[str], dict[str, Role]]:
    category_names = set(db.scalars(select(Category.name)).all())
    role_rows = db.scalars(select(Role)).all()
    role_by_name = {r.name: r for r in role_rows}
    return category_names, role_by_name


def _insert_single_import_question(
    db: Session,
    item: ImportQuestionItem,
    category_names: set[str],
    role_by_name: dict[str, Role],
) -> tuple[Question, dict]:
    """
    Create one question (with AI reference answer), relations; flush within current transaction.
    Caller must commit or rollback.
    """
    raw_cat = (item.category_name or "").strip()
    raw_roles = list(item.roles or [])
    cat, role_names = _normalize_for_commit(item, category_names, role_by_name)
    category_fallback = raw_cat not in category_names
    roles_adjusted = set(role_names) != set(raw_roles)

    q = Question(
        stem=item.stem.strip(),
        category=cat,
        difficulty=item.difficulty,
        reference_answer=call_doubao_reference_answer(item.stem.strip()),
    )
    db.add(q)
    db.flush()

    linked_roles = 0
    for role_name in set(role_names):
        rel = QuestionRole(question_id=q.id, role_id=role_by_name[role_name].id)
        db.add(rel)
        linked_roles += 1

    created_companies = 0
    linked_companies = 0
    for company_name_raw in set(item.companies):
        company_name = company_name_raw.strip()
        if not company_name:
            continue
        company = db.scalar(select(Company).where(Company.name == company_name))
        if not company:
            company = Company(name=company_name)
            db.add(company)
            db.flush()
            created_companies += 1
        rel = QuestionCompany(question_id=q.id, company_id=company.id)
        db.add(rel)
        linked_companies += 1

    stats = {
        "category_fallback": category_fallback,
        "roles_adjusted": roles_adjusted,
        "linked_roles": linked_roles,
        "linked_companies": linked_companies,
        "created_companies": created_companies,
    }
    return q, stats


def _build_extract_prompt(categories: list[str], roles: list[str]) -> str:
    return f"""
你是面试题结构化提取器。请严格输出 JSON，不允许输出任何解释文字。
禁止输出思考过程、推理过程、分析过程、草稿；只输出最终 JSON 结果。
如果无法提取，返回 {{"questions":[]}}。

重要约束：
1) 公司名称必须返回全称，不允许简称。示例：必须返回“字节跳动”，不能返回“字节”。
2) category_name 必须且只能从以下列表中选择一个：
{categories}
3) roles 中每一个岗位必须且只能从以下列表中选择：
{roles}
4) 若不确定公司全称，请根据上下文推断并返回最常见全称，不要用简称。
5) 输出必须精简，禁止长段解释。
6) 输出格式严格为：
{{
  "questions": [
    {{
      "stem": "string",
      "category_name": "string",
      "roles": ["string"],
      "companies": ["string"],
      "difficulty": 1-5
    }}
  ]
}}
""".strip()


def _split_text_for_extract(raw_text: str, max_chars: int = 1200) -> list[str]:
    # Prefer splitting on paragraph/newline boundaries to avoid breaking a question body.
    normalized = raw_text.replace("\r\n", "\n")
    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    if not paragraphs:
        return [raw_text]

    chunks: list[str] = []
    current = ""

    def flush_current() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
            current = ""

    for para in paragraphs:
        next_piece = f"{current}\n\n{para}".strip() if current else para
        if len(next_piece) <= max_chars:
            current = next_piece
            continue

        # current chunk first
        flush_current()

        # if single paragraph is still too large, split by lines (still newline-safe)
        if len(para) > max_chars:
            lines = [line.strip() for line in para.split("\n") if line.strip()]
            line_bucket = ""
            for line in lines:
                line_next = f"{line_bucket}\n{line}".strip() if line_bucket else line
                if len(line_next) <= max_chars:
                    line_bucket = line_next
                else:
                    if line_bucket:
                        chunks.append(line_bucket)
                    # Extreme fallback: split a very long line only when unavoidable
                    if len(line) > max_chars * 2:
                        start = 0
                        step = max_chars
                        while start < len(line):
                            chunks.append(line[start : start + step].strip())
                            start += step
                        line_bucket = ""
                    else:
                        line_bucket = line
            if line_bucket:
                chunks.append(line_bucket)
        else:
            current = para

    flush_current()
    return chunks


def _normalize_stem(stem: str) -> str:
    return "".join(stem.lower().split())


@router.get("/prompt-template")
def get_import_prompt_template(db: Session = Depends(get_db)):
    categories = db.scalars(select(Category.name).order_by(Category.name.asc())).all()
    roles = db.scalars(select(Role.name).order_by(Role.name.asc())).all()
    if not categories or not roles:
        raise HTTPException(status_code=400, detail="Please create categories and roles first")

    prompt = _build_extract_prompt(categories, roles)
    return {"prompt": prompt, "allowed_categories": categories, "allowed_roles": roles}


@router.post("/preview")
def import_preview(payload: ImportPreviewRequest, db: Session = Depends(get_db)):
    categories = db.scalars(select(Category.name).order_by(Category.name.asc())).all()
    roles = db.scalars(select(Role.name).order_by(Role.name.asc())).all()
    if not categories or not roles:
        raise HTTPException(status_code=400, detail="Please create categories and roles first")

    prompt = _build_extract_prompt(categories, roles)
    chunks = _split_text_for_extract(payload.raw_text, max_chars=1200)
    merged_questions: list[dict] = []
    seen_stems: set[str] = set()
    chunk_errors: list[dict] = []
    ai_raw_list: list[dict] = []

    for idx, chunk in enumerate(chunks):
        try:
            ai_json, ai_raw = call_doubao_extract(prompt=prompt, raw_text=chunk)
            if settings.ai_debug_raw_response:
                ai_raw_list.append({"chunk_index": idx + 1, "raw": ai_raw})
            questions = ai_json.get("questions", [])
            if not isinstance(questions, list):
                chunk_errors.append({"chunk_index": idx + 1, "message": "questions is not a list"})
                continue
            for q in questions:
                if not isinstance(q, dict):
                    continue
                stem = str(q.get("stem", "")).strip()
                if not stem:
                    continue
                key = _normalize_stem(stem)
                if key in seen_stems:
                    continue
                seen_stems.add(key)
                merged_questions.append(q)
        except HTTPException as exc:
            chunk_errors.append({"chunk_index": idx + 1, "detail": exc.detail})

    if not merged_questions:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "AI extraction failed for all chunks",
                "chunks": len(chunks),
                "chunk_errors": chunk_errors,
            },
        )

    resp = {
        "questions": merged_questions,
        "allowed_categories": categories,
        "allowed_roles": roles,
        "chunk_count": len(chunks),
        "chunk_error_count": len(chunk_errors),
        "chunk_errors": chunk_errors,
    }
    if settings.ai_debug_raw_response:
        resp["ai_raw"] = ai_raw_list
    return resp


@router.post("/commit-one", response_model=ImportCommitOneResponse)
def import_commit_one(payload: ImportQuestionItem, db: Session = Depends(get_db)):
    """Generate reference answer and persist one question; safe if batch import fails mid-way elsewhere."""
    category_names, role_by_name = _load_taxonomy(db)
    if not category_names or not role_by_name:
        raise HTTPException(status_code=400, detail="Please create categories and roles first")
    try:
        q, stats = _insert_single_import_question(db, payload, category_names, role_by_name)
        db.commit()
        db.refresh(q)
    except Exception:
        db.rollback()
        raise
    return ImportCommitOneResponse(
        id=q.id,
        stem=q.stem,
        category=q.category,
        difficulty=q.difficulty,
        category_fallback=stats["category_fallback"],
        roles_adjusted=stats["roles_adjusted"],
        linked_roles=stats["linked_roles"],
        linked_companies=stats["linked_companies"],
        created_companies=stats["created_companies"],
    )


@router.post("/commit")
def import_commit(payload: ImportPayload, db: Session = Depends(get_db)):
    category_names, role_by_name = _load_taxonomy(db)

    if not category_names or not role_by_name:
        raise HTTPException(status_code=400, detail="Please create categories and roles first")

    created_questions = 0
    created_companies = 0
    linked_roles = 0
    linked_companies = 0
    category_fallbacks = 0
    role_lists_adjusted = 0

    try:
        for item in payload.questions:
            _, stats = _insert_single_import_question(db, item, category_names, role_by_name)
            created_questions += 1
            if stats["category_fallback"]:
                category_fallbacks += 1
            if stats["roles_adjusted"]:
                role_lists_adjusted += 1
            created_companies += stats["created_companies"]
            linked_roles += stats["linked_roles"]
            linked_companies += stats["linked_companies"]
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "created_questions": created_questions,
        "created_companies": created_companies,
        "linked_roles": linked_roles,
        "linked_companies": linked_companies,
        "category_fallbacks": category_fallbacks,
        "role_lists_adjusted": role_lists_adjusted,
    }

