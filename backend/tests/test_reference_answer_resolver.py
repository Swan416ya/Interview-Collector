from unittest.mock import patch

from app.services.reference_answer_resolver import resolve_reference_for_stem


def test_skip_when_existing_reference() -> None:
    with patch("app.services.reference_answer_resolver.call_doubao_reference_answer") as mock_ai:
        out = resolve_reference_for_stem("  Q?  ", existing_reference="  already  ")
        assert out == "already"
        mock_ai.assert_not_called()


def test_batch_cache_single_ai_call() -> None:
    cache: dict[str, str] = {}
    with patch("app.services.reference_answer_resolver.call_doubao_reference_answer") as mock_ai:
        mock_ai.return_value = "REF-A"
        a = resolve_reference_for_stem("Same stem", batch_cache=cache)
        b = resolve_reference_for_stem("same stem", batch_cache=cache)
        assert a == "REF-A" and b == "REF-A"
        mock_ai.assert_called_once()
