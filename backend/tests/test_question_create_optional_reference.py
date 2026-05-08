from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_create_question_skips_ai_when_reference_answer_provided() -> None:
    with TestClient(app) as client, patch(
        "app.services.reference_answer_resolver.call_doubao_reference_answer"
    ) as mock_ref:
        res = client.post(
            "/api/questions",
            json={
                "stem": "Pytest manual question stem here",
                "category": "未分类",
                "difficulty": 3,
                "reference_answer": "manual-ref-no-ai",
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["reference_answer"] == "manual-ref-no-ai"
        mock_ref.assert_not_called()
