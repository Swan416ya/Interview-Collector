"""Shared stem normalization for dedupe keys and reference-answer batch cache."""


def stem_fingerprint(stem: str) -> str:
    """Lowercase, strip outer whitespace, remove all internal whitespace (matches import preview dedupe)."""
    return "".join(stem.strip().lower().split())
