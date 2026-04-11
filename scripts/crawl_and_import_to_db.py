#!/usr/bin/env python3
"""
1) Crawl JavaGuide + 小林coding (reuse crawl_interview_guides logic).
2) Split each page by ### / #### into stem + reference_answer (no AI).
3) Insert into local Interview Collector DB; company = 渠道名.

Run from repo root OR backend dir (script will chdir to backend for DATABASE_URL).

  cd backend
  ..\\.venv\\Scripts\\python.exe ..\\scripts\\crawl_and_import_to_db.py --max-pages 2000 --delay 0.4
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SCRIPTS = ROOT / "scripts"

# SQLite path in config is relative to CWD — force backend as cwd before importing app
os.chdir(BACKEND)
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.question import Question  # noqa: E402
from app.models.taxonomy import Category, Company, QuestionCompany  # noqa: E402

SKIP_STEMS = frozenset(
    {
        "目录",
        "推荐阅读",
        "扩展阅读",
        "参考资料",
        "公众号",
        "Star 趋势",
        "贡献者",
        "最近更新",
    }
)

# (regex on source url path + filename), category name must exist in DB or skipped
PATH_CATEGORY_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"mysql", re.I), "MySQL"),
    (re.compile(r"redis", re.I), "Redis"),
    (re.compile(r"mongo", re.I), "MongoDB"),
    (re.compile(r"network|tcp|http|ip/|图解网络", re.I), "计算机网络"),
    (re.compile(r"operating|linux|图解系统|进程|内存管理", re.I), "操作系统"),
    (re.compile(r"java(?!script)", re.I), "Java"),
    (re.compile(r"\bgo\b|golang|图解.*go", re.I), "Go"),
    (re.compile(r"spring", re.I), "Spring"),
    (re.compile(r"mq|kafka|消息队列|rocket", re.I), "消息队列"),
    (re.compile(r"分布式", re.I), "分布式"),
    (re.compile(r"算法|leetcode", re.I), "数据结构与算法"),
    (re.compile(r"系统设计|场景题", re.I), "系统设计"),
    (re.compile(r"ai/|llm|agent|rag|大模型", re.I), "AI 应用开发"),
    (re.compile(r"jvm", re.I), "JVM"),
    (re.compile(r"docker|k8s|kubernetes", re.I), "Docker"),
]


def _load_crawler():
    path = SCRIPTS / "crawl_interview_guides.py"
    spec = importlib.util.spec_from_file_location("guide_crawl", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _strip_frontmatter(md: str) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    if not md.startswith("---\n"):
        return meta, md
    parts = md.split("---", 2)
    if len(parts) < 3:
        return meta, md
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip("'\"")
    return meta, parts[2].lstrip("\n")


def _split_into_qa(md_body: str) -> list[tuple[str, str]]:
    """Split on ### / #### headings; stem = heading text, body = until next same-level block."""
    pat = re.compile(r"^#{3,4}\s+(.+)$", re.M)
    matches = list(pat.finditer(md_body))
    out: list[tuple[str, str]] = []
    if not matches:
        h1 = re.search(r"^#\s+(.+)$", md_body, re.M)
        stem = h1.group(1).strip() if h1 else ""
        body = md_body.strip()
        if len(stem) >= 3 and len(body) > 80:
            out.append((stem, body))
        return out

    for i, m in enumerate(matches):
        stem = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_body)
        body = md_body[start:end].strip()
        if len(stem) < 3 or len(body) < 20:
            continue
        if stem in SKIP_STEMS:
            continue
        out.append((stem, body))
    return out


def _guess_category(source_url: str, slug: str, category_names: set[str]) -> str:
    blob = f"{source_url} {slug}"
    for rx, name in PATH_CATEGORY_RULES:
        if not rx.search(blob):
            continue
        if name in category_names:
            return name
        return name[:64]
    if "未分类" in category_names:
        return "未分类"
    return (sorted(category_names)[0] if category_names else "未分类")[:64]


def _ensure_base_taxonomy(db) -> set[str]:
    names = set(db.scalars(select(Category.name)).all())
    if not names:
        db.add(Category(name="未分类"))
        db.commit()
        names = set(db.scalars(select(Category.name)).all())
    return names


def _ensure_company(db, name: str) -> Company:
    co = db.scalar(select(Company).where(Company.name == name))
    if not co:
        co = Company(name=name)
        db.add(co)
        db.flush()
    return co


def import_markdown_dir(
    base: Path,
    channel: str,
    db,
    category_names: set[str],
    company: Company,
    skip_existing_stems: bool,
) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    stems_in_db: set[str] = set()
    if skip_existing_stems:
        stems_in_db = set(db.scalars(select(Question.stem)).all())

    site_dir = base / channel
    if not site_dir.is_dir():
        return 0, 0

    for fpath in sorted(site_dir.glob("*.md")):
        text = fpath.read_text(encoding="utf-8")
        meta, body = _strip_frontmatter(text)
        source = meta.get("source", "")
        pairs = _split_into_qa(body)
        cat = _guess_category(source, fpath.name, category_names)

        for stem, ref in pairs:
            stem = stem.strip()
            if len(stem) > 4000:
                stem = stem[:3997] + "..."
            if skip_existing_stems and stem in stems_in_db:
                skipped += 1
                continue
            if db.scalar(select(Question.id).where(Question.stem == stem)):
                skipped += 1
                stems_in_db.add(stem)
                continue

            q = Question(
                stem=stem,
                category=cat,
                difficulty=3,
                reference_answer=ref,
            )
            db.add(q)
            db.flush()
            db.add(QuestionCompany(question_id=q.id, company_id=company.id))
            stems_in_db.add(stem)
            inserted += 1

        if inserted and inserted % 100 == 0:
            db.commit()
            print(f"  ... committed batch, total inserted so far: {inserted}")

    db.commit()
    return inserted, skipped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "crawled_guides")
    ap.add_argument("--delay", type=float, default=0.45)
    ap.add_argument("--max-pages", type=int, default=2500, help="Per site fetch attempts cap")
    ap.add_argument("--timeout", type=float, default=35.0)
    ap.add_argument("--skip-crawl", action="store_true", help="Only import existing MD under --out")
    ap.add_argument("--no-skip-duplicate-stem", action="store_true")
    args = ap.parse_args()

    crawl = _load_crawler()

    if not args.skip_crawl:
        args.out.mkdir(parents=True, exist_ok=True)
        sites = [
            (
                "javaguide",
                ["https://javaguide.cn/home.html", "https://javaguide.cn/"],
                "JavaGuide",
            ),
            ("xiaolin", ["https://www.xiaolincoding.com/"], "小林coding"),
        ]
        for site_key, seeds, _label in sites:
            print(f"\n=== Crawl {site_key} → {args.out / site_key} ===")
            t0 = time.perf_counter()
            ok, bad = crawl.crawl_site(site_key, seeds, args.out, args.delay, args.max_pages, args.timeout)
            print(f"saved={ok} failed/skipped={bad} elapsed={time.perf_counter() - t0:.1f}s")
    else:
        print("Skip crawl, import only.")

    print("\n=== Import to DB (cwd=%s) ===" % os.getcwd())
    db = SessionLocal()
    try:
        category_names = _ensure_base_taxonomy(db)
        co_j = _ensure_company(db, "JavaGuide")
        co_x = _ensure_company(db, "小林coding")

        skip_dup = not args.no_skip_duplicate_stem
        ij, sj = import_markdown_dir(args.out, "javaguide", db, category_names, co_j, skip_dup)
        print(f"JavaGuide: inserted={ij} skipped={sj}")

        ix, sx = import_markdown_dir(args.out, "xiaolin", db, category_names, co_x, skip_dup)
        print(f"小林coding: inserted={ix} skipped={sx}")
    finally:
        db.close()

    print("Done.")


if __name__ == "__main__":
    main()
