"""Pytest bootstrap: force in-memory SQLite + dummy AI env before app imports."""

from __future__ import annotations

import os

# Must run before importing app.* which loads Settings from env.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AI_API_KEY", "pytest-dummy-key")
os.environ.setdefault("AI_MODEL", "pytest-dummy-model")
