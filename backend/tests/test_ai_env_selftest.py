"""
联机 AI 冒烟：默认跳过，避免 CI/无网环境失败。

验收时在 backend 目录执行（需可访问 .env 中的 AI_BASE_URL）：

  set RUN_AI_ENV_SELFTEST=1
  pytest tests/test_ai_env_selftest.py -q

或直接：

  python scripts/selftest_ai_env.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    os.environ.get("RUN_AI_ENV_SELFTEST") != "1",
    reason="设置环境变量 RUN_AI_ENV_SELFTEST=1 后运行以联机验证 backend/.env 中的 AI 配置",
)
def test_ai_env_selftest_script_exits_zero() -> None:
    script = _BACKEND / "scripts" / "selftest_ai_env.py"
    spec = importlib.util.spec_from_file_location("selftest_ai_env", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rc = mod.main()
    assert rc == 0, f"selftest_ai_env.main() returned {rc}"
