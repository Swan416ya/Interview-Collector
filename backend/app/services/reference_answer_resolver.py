import logging

from app.core.stem_norm import stem_fingerprint
from app.services.ai_service import call_doubao_reference_answer

logger = logging.getLogger(__name__)


def resolve_reference_for_stem(
    stem: str,
    *,
    existing_reference: str | None = None,
    batch_cache: dict[str, str] | None = None,
) -> str:
    """
    Return reference answer text, calling the AI provider at most once per unique stem fingerprint
    when ``batch_cache`` is provided. Skip AI entirely if ``existing_reference`` is non-empty.
    """
    stem_clean = stem.strip()
    if existing_reference is not None and existing_reference.strip():
        logger.info(
            "reference_answer skip_ai reason=already_present stem_len=%s",
            len(stem_clean),
        )
        return existing_reference.strip()

    key = stem_fingerprint(stem_clean)
    if batch_cache is not None and key in batch_cache:
        logger.info(
            "reference_answer skip_ai reason=batch_cache stem_len=%s key_prefix=%s",
            len(stem_clean),
            key[:32],
        )
        return batch_cache[key]

    text = call_doubao_reference_answer(stem_clean)
    if batch_cache is not None:
        batch_cache[key] = text
    return text
