"""Pytest bootstrap: file-backed SQLite (pooled :memory: breaks create_all vs get_db) + dummy AI env."""

from __future__ import annotations

import os
from pathlib import Path

# Must run before importing app.* which loads Settings from env.
_backend = Path(__file__).resolve().parent.parent
_test_db = _backend / ".pytest_interview.db"
if _test_db.exists():
    _test_db.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.as_posix()}"
os.environ.setdefault("AI_API_KEY", "pytest-dummy-key")
os.environ.setdefault("AI_MODEL", "pytest-dummy-model")
