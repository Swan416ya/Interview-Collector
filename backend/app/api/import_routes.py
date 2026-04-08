from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.question import Question
from app.models.taxonomy import Category, Company, QuestionCompany, QuestionRole, Role
from app.schemas.importing import ImportPayload

router = APIRouter(prefix="/api/import", tags=["import"])


@router.get("/prompt-template")
def get_import_prompt_template(db: Session = Depends(get_db)):
    categories = db.scalars(select(Category.name).order_by(Category.name.asc())).all()
    roles = db.scalars(select(Role.name).order_by(Role.name.asc())).all()
    if not categories or not roles:
        raise HTTPException(status_code=400, detail="Please create categories and roles first")

    prompt = f"""
你是面试题结构化提取器。请严格输出 JSON，不允许输出任何解释文字。

重要约束：
1) 公司名称必须返回全称，不允许简称。示例：必须返回“字节跳动”，不能返回“字节”。
2) category_name 必须且只能从以下列表中选择一个：
{categories}
3) roles 中每一个岗位必须且只能从以下列表中选择：
{roles}
4) 若不确定公司全称，请根据上下文推断并返回最常见全称，不要用简称。
5) 输出格式严格为：
{{
  "questions": [
    {{
      "stem": "string",
      "category_name": "string",
      "roles": ["string"],
      "companies": ["string"],
      "difficulty": 1-5,
      "answer_reference": "string"
    }}
  ]
}}
""".strip()
    return {"prompt": prompt, "allowed_categories": categories, "allowed_roles": roles}


@router.post("/commit")
def import_commit(payload: ImportPayload, db: Session = Depends(get_db)):
    category_names = set(db.scalars(select(Category.name)).all())
    role_rows = db.scalars(select(Role)).all()
    role_by_name = {r.name: r for r in role_rows}

    if not category_names or not role_by_name:
        raise HTTPException(status_code=400, detail="Please create categories and roles first")

    created_questions = 0
    created_companies = 0
    linked_roles = 0
    linked_companies = 0

    for item in payload.questions:
        if item.category_name not in category_names:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category_name: {item.category_name}. Must be one of local categories.",
            )
        invalid_roles = [r for r in item.roles if r not in role_by_name]
        if invalid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid roles: {invalid_roles}. Roles must be from local role list.",
            )

        q = Question(stem=item.stem.strip(), category=item.category_name, difficulty=item.difficulty)
        db.add(q)
        db.flush()
        created_questions += 1

        for role_name in set(item.roles):
            rel = QuestionRole(question_id=q.id, role_id=role_by_name[role_name].id)
            db.add(rel)
            linked_roles += 1

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

    db.commit()
    return {
        "created_questions": created_questions,
        "created_companies": created_companies,
        "linked_roles": linked_roles,
        "linked_companies": linked_companies,
    }

