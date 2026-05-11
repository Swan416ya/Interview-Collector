from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

_FAKE_SUMMARY = {
    "summary_text": "整体掌握尚可，建议巩固薄弱概念。",
    "dimensions": [
        {"key": "correctness", "label": "正确性", "score": 7},
        {"key": "completeness", "label": "完整性", "score": 7},
        {"key": "articulation", "label": "表达力", "score": 7},
        {"key": "depth", "label": "知识深度", "score": 6},
        {"key": "consistency", "label": "稳定性", "score": 7},
    ],
}


@patch("app.services.session_summary_service.call_doubao_session_summary")
@patch("app.api.practice_routes.call_doubao_grade")
def test_session_summary_on_summary_endpoint(mock_grade, mock_summary) -> None:
    mock_grade.return_value = {"score": 7, "analysis": "ok"}
    mock_summary.return_value = _FAKE_SUMMARY

    with TestClient(app) as client:
        ids: list[int] = []
        for i in range(5):
            r = client.post(
                "/api/questions",
                json={
                    "stem": f"session-summary-stem-{i}-minimum-length-ok",
                    "category": "未分类",
                    "difficulty": 3,
                    "reference_answer": "r",
                },
            )
            assert r.status_code == 200, r.text
            ids.append(int(r.json()["id"]))
        start = client.post("/api/practice/sessions/start/custom", json={"question_ids": ids})
        assert start.status_code == 200, start.text
        sid = int(start.json()["session_id"])
        for qid in ids:
            sub = client.post(
                f"/api/practice/sessions/{sid}/submit",
                json={"question_id": qid, "user_answer": f"answer-{qid}"},
            )
            assert sub.status_code == 200, sub.text

        summ = client.get(f"/api/practice/sessions/{sid}/summary")
        assert summ.status_code == 200, summ.text
        body = summ.json()
        assert body.get("feedback") is not None
        assert len(body["feedback"]["dimensions"]) == 5
        assert body["summary_pending"] is False
        mock_summary.assert_called()
