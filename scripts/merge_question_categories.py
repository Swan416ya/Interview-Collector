"""
Merge duplicate / fragmented question categories into canonical names.

Updates:
  - questions.category (all rows matching each source name)
  - categories table: ensure targets exist; remove obsolete category rows

Re-run is safe: sources already empty become no-op; targets already exist for Category INSERT.

Usage:
  backend\\.venv\\Scripts\\python.exe scripts\\merge_question_categories.py
  backend\\.venv\\Scripts\\python.exe scripts\\merge_question_categories.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import func, select, update

from app.core.database import SessionLocal
from app.models.question import Question
from app.models.taxonomy import Category

# source -> target (canonical)
MERGE_MAP: list[tuple[str, str]] = [
    ("Java/JVM", "Java"),
    ("Java基础", "Java"),
    ("Spring", "Java"),
    ("JavaScript基础", "前端"),
    ("JavaScript", "前端"),
    ("Vue", "前端"),
    ("数据库", "MySQL"),
    ("数据库与架构", "MySQL"),
    ("前端基础", "前端"),
    ("前端框架", "前端"),
    ("算法", "数据结构"),
    ("面试综合", "综合"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes only")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print("=== Category merge ===\n")
        for src, dst in MERGE_MAP:
            cnt = db.scalar(select(func.count()).select_from(Question).where(Question.category == src)) or 0
            print(f"  {src!r} -> {dst!r}  ({cnt} questions)")
            if cnt and not args.dry_run:
                db.execute(update(Question).where(Question.category == src).values(category=dst))

        if not args.dry_run:
            db.flush()
            # Ensure taxonomy rows for every canonical target we use
            existing = set(db.scalars(select(Category.name)).all())
            for _, dst in MERGE_MAP:
                if dst not in existing:
                    db.add(Category(name=dst))
                    existing.add(dst)
                    print(f"\n[Category table] INSERT {dst!r}")
            db.flush()

            # Remove taxonomy entries for merged-away names (questions no longer use them)
            for src, _ in MERGE_MAP:
                row = db.scalar(select(Category).where(Category.name == src))
                if row:
                    still = db.scalar(
                        select(func.count()).select_from(Question).where(Question.category == src)
                    )
                    if int(still or 0) == 0:
                        db.delete(row)
                        print(f"[Category table] DELETE {src!r}")
                    else:
                        print(f"[Category table] KEEP {src!r} (still {still} questions — check manually)")

            db.commit()

        print("\n=== Distinct question categories ===")
        rows = db.execute(
            select(Question.category, func.count(Question.id)).group_by(Question.category).order_by(Question.category.asc())
        ).all()
        for cat, n in rows:
            print(f"  {cat or '(empty)'}: {n}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if args.dry_run:
        print("\n(dry-run: no database changes written)")


if __name__ == "__main__":
    main()
