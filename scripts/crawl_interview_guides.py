#!/usr/bin/env python3
"""
Crawl public HTML pages from JavaGuide (javaguide.cn) and 小林coding (xiaolincoding.com),
save main body as Markdown-ish text files. No AI — plain HTTP + HTML parse only.

IMPORTANT — legal & ethics
----------------------------
- Site content is copyrighted (e.g. JavaGuide / 小林coding). Use only for **personal study**
  and respect robots.txt, rate limits, and each site’s terms of service.
- This script is a **technical helper**; you are responsible for compliance.
- References: https://javaguide.cn/home.html , https://www.xiaolincoding.com/

Usage (from repo root):
  pip install -r scripts/requirements-crawl.txt
  python scripts/crawl_interview_guides.py --site all --out data/crawled_guides --delay 0.8

  python scripts/crawl_interview_guides.py --site javaguide --max-pages 400
  python scripts/crawl_interview_guides.py --site xiaolin --max-pages 800
"""

from __future__ import annotations

import argparse
import html
import re
import time
from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

DEFAULT_UA = (
    "InterviewCollectorCrawler/1.0 (+local; personal study; "
    "contact: see repo README)"
)

# Try common VitePress / VuePress / doc theme wrappers (order matters).
CONTENT_SELECTORS = [
    "main .vp-doc",
    "main .content",
    ".vp-doc",
    "article.vp-doc",
    "main article",
    ".theme-default-content",
    ".markdown-body",
    "[class*='markdown-body']",
    "article",
    "main",
]

SKIP_PATH_SUBSTR = (
    "/assets/",
    "/img/",
    "/images/",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    "mailto:",
)

# Optional: skip obvious non-article areas (still allow most interview content).
EXCLUDE_PATH_REGEX = re.compile(
    r"(^/(?:search|tag)(?:/|$))|"
    r"\.(xml|json|txt|js|css|map)$",
    re.I,
)


def _host_allowed(netloc: str, site: str) -> bool:
    n = netloc.lower().rstrip(".")
    if site == "javaguide":
        return n in ("javaguide.cn", "www.javaguide.cn", "interview.javaguide.cn")
    if site == "xiaolin":
        return n in ("www.xiaolincoding.com", "xiaolincoding.com")
    return False


def _normalize_url(site: str, base: str, href: str) -> str | None:
    href = (href or "").strip()
    if not href or href.startswith("#"):
        return None
    full = urljoin(base, href)
    full, _frag = urldefrag(full)
    p = urlparse(full)
    if p.scheme not in ("http", "https"):
        return None
    if not _host_allowed(p.netloc, site):
        return None
    path = p.path or "/"
    low = full.lower()
    if any(s in low for s in SKIP_PATH_SUBSTR):
        return None
    if EXCLUDE_PATH_REGEX.search(path):
        return None
    # Prefer canonical html pages; allow extensionless doc paths.
    if path.endswith("/"):
        full = f"{p.scheme}://{p.netloc}{path.rstrip('/') or '/'}"
        if p.query:
            full += f"?{p.query}"
        return full
    if "." in Path(path).name:
        ext = Path(path).suffix.lower()
        if ext not in (".html", ".htm"):
            return None
    return full


def _pick_main_soup(soup: BeautifulSoup) -> BeautifulSoup | None:
    for sel in CONTENT_SELECTORS:
        node = soup.select_one(sel)
        if node and len(node.get_text(strip=True)) > 200:
            return node
    return None


def _soup_to_markdownish(root: BeautifulSoup) -> str:
    """Very small HTML→text: headings/blocks preserved loosely; good enough for 八股归档."""

    def walk(el) -> list[str]:
        lines: list[str] = []
        name = el.name if hasattr(el, "name") else None
        if name is None:
            t = str(el).strip()
            if t:
                lines.append(html.unescape(t))
            return lines

        if name in ("script", "style", "noscript", "svg", "canvas"):
            return lines

        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            lev = int(name[1])
            text = el.get_text(" ", strip=True)
            if text:
                lines.append(f"\n{'#' * lev} {text}\n")
            return lines

        if name == "p":
            text = el.get_text(" ", strip=True)
            if text:
                lines.append(text + "\n")
            return lines

        if name in ("ul", "ol"):
            for li in el.find_all("li", recursive=False):
                t = li.get_text(" ", strip=True)
                if t:
                    lines.append(f"- {t}\n")
            lines.append("")
            return lines

        if name == "pre":
            code = el.get_text()
            if code.strip():
                lines.append("\n```\n" + code.rstrip() + "\n```\n")
            return lines

        if name == "blockquote":
            t = el.get_text(" ", strip=True)
            if t:
                lines.append("\n> " + t + "\n")
            return lines

        for child in el.children:
            lines.extend(walk(child))
        return lines

    parts = walk(root)
    text = "\n".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _page_title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    t = soup.find("title")
    if t and t.string:
        return t.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return "untitled"


def crawl_site(
    site: str,
    seeds: list[str],
    out_root: Path,
    delay: float,
    max_pages: int,
    timeout: float,
) -> tuple[int, int]:
    out_dir = out_root / site
    out_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    queue: deque[str] = deque(seeds)
    ok = 0
    fail = 0

    headers = {"User-Agent": DEFAULT_UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}

    with httpx.Client(follow_redirects=True, headers=headers, timeout=timeout) as client:
        while queue and ok + fail < max_pages:
            url = queue.popleft()
            if url in seen:
                continue
            seen.add(url)

            try:
                r = client.get(url)
                if r.status_code != 200:
                    fail += 1
                    continue
                ctype = r.headers.get("content-type", "")
                if "text/html" not in ctype and "application/xhtml" not in ctype:
                    fail += 1
                    continue
                soup = BeautifulSoup(r.text, "html.parser")
                main = _pick_main_soup(soup)
                if not main:
                    fail += 1
                    continue

                title = _page_title(soup)
                body = _soup_to_markdownish(main)
                if len(body) < 120:
                    fail += 1
                    continue

                p = urlparse(url)
                slug = (p.path or "/").strip("/").replace("/", "__")
                if not slug:
                    slug = "index"
                if p.netloc.lower().startswith("interview."):
                    slug = "interview__" + slug
                fname = re.sub(r'[^a-zA-Z0-9_\-\u4e00-\u9fff.]+', "_", slug)[:180] + ".md"
                fpath = out_dir / fname

                front = f"---\nsource: {url}\ntitle: {title!r}\n---\n\n"
                fpath.write_text(front + f"# {title}\n\n" + body + "\n", encoding="utf-8")
                ok += 1

                for a in soup.find_all("a", href=True):
                    nu = _normalize_url(site, url, a["href"])
                    if nu and nu not in seen:
                        queue.append(nu)

            except Exception:
                fail += 1

            if delay > 0:
                time.sleep(delay)

    return ok, fail


def main() -> None:
    ap = argparse.ArgumentParser(description="Crawl JavaGuide / 小林coding as local Markdown.")
    ap.add_argument(
        "--site",
        choices=("javaguide", "xiaolin", "all"),
        default="all",
        help="Which site to crawl",
    )
    ap.add_argument("--out", type=Path, default=Path("data/crawled_guides"), help="Output directory")
    ap.add_argument("--delay", type=float, default=0.8, help="Seconds between requests (be polite)")
    ap.add_argument("--max-pages", type=int, default=2500, help="Max pages to fetch per site")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    sites: list[tuple[str, list[str]]] = []
    if args.site in ("javaguide", "all"):
        sites.append(
            (
                "javaguide",
                [
                    "https://javaguide.cn/home.html",
                    "https://javaguide.cn/",
                ],
            )
        )
    if args.site in ("xiaolin", "all"):
        sites.append(
            (
                "xiaolin",
                [
                    "https://www.xiaolincoding.com/",
                ],
            )
        )

    args.out.mkdir(parents=True, exist_ok=True)
    print("Output:", args.out.resolve())
    for site, seeds in sites:
        print(f"\n=== Crawling {site} (seeds={len(seeds)}, max_pages={args.max_pages}) ===")
        t0 = time.perf_counter()
        ok, bad = crawl_site(site, seeds, args.out, args.delay, args.max_pages, args.timeout)
        dt = time.perf_counter() - t0
        print(f"Done {site}: saved={ok}, skipped/failed={bad}, elapsed={dt:.1f}s")


if __name__ == "__main__":
    main()
