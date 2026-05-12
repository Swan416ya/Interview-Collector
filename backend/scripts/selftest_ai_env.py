"""
使用 backend/.env（经 app.core.config）对 AI 做一次冒烟自测。

- openai_compatible：走练习阅卷流式 iter_grade_stream_events（与线上 submit-stream 一致）
- ark_responses：走一次 call_doubao_grade 非流式

用法（在 backend 目录或任意目录均可）:
  python scripts/selftest_ai_env.py

退出码：0 成功；1 失败；2 缺少 AI_API_KEY / AI_MODEL
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.core.config import settings  # noqa: E402
from app.services.ai_service import (  # noqa: E402
    _normalize_ai_provider,
    call_doubao_grade,
    iter_grade_stream_events,
)


def _fail(msg: str) -> int:
    print(f"[selftest_ai_env] FAIL: {msg}", file=sys.stderr)
    return 1


def _stream_selftest() -> int:
    graded: dict | None = None
    n_reason = 0
    for kind, payload in iter_grade_stream_events("1+1等于几？", "2"):
        if kind == "reasoning":
            n_reason += 1
        elif kind == "graded":
            if isinstance(payload, dict):
                graded = payload
        elif kind == "error":
            return _fail(str(payload))

    if not graded:
        return _fail("未收到 graded 事件")
    if "score" not in graded or "analysis" not in graded:
        return _fail(f"graded 结构异常: {graded!r}")
    print(
        f"[selftest_ai_env] OK stream provider=openai_compatible "
        f"reasoning_chunks={n_reason} score={graded.get('score')}"
    )
    return 0


def _ark_selftest() -> int:
    try:
        g = call_doubao_grade("1+1=?", "2")
    except Exception as exc:  # noqa: BLE001 — 冒烟脚本需要打印底层错误
        return _fail(f"call_doubao_grade: {exc}")
    if not isinstance(g, dict) or "score" not in g:
        return _fail(f"graded 结构异常: {g!r}")
    print(f"[selftest_ai_env] OK ark_responses score={g.get('score')}")
    return 0


def main() -> int:
    if not settings.ai_api_key.strip() or not settings.ai_model.strip():
        print("[selftest_ai_env] FAIL: 缺少 AI_API_KEY 或 AI_MODEL", file=sys.stderr)
        return 2

    prov = _normalize_ai_provider()
    print(
        f"[selftest_ai_env] start provider={prov!r} "
        f"base_url={settings.ai_base_url!r} model={settings.ai_model!r}",
        flush=True,
    )

    if prov == "openai_compatible":
        return _stream_selftest()
    if prov == "ark_responses":
        return _ark_selftest()
    return _fail(f"不支持的 AI_PROVIDER 归一化结果: {prov!r}")


if __name__ == "__main__":
    raise SystemExit(main())
