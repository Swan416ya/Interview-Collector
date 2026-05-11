from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def _create_question(client: TestClient) -> int:
    r = client.post(
        "/api/questions",
        json={
            "stem": "wrongbook-test-stem-minimum-length-ok",
            "category": "未分类",
            "difficulty": 3,
            "reference_answer": "ref",
        },
    )
    assert r.status_code == 200, r.text
    return int(r.json()["id"])


@patch("app.api.practice_routes.call_doubao_grade")
def test_wrongbook_admits_on_low_ai_score(mock_grade) -> None:
    mock_grade.return_value = {"score": 4, "analysis": "weak"}
    with TestClient(app) as client:
        qid = _create_question(client)
        sub = client.post(
            "/api/practice/daily/submit",
            json={"question_id": qid, "user_answer": "incomplete answer"},
        )
        assert sub.status_code == 200, sub.text
        page = client.get("/api/practice/wrongbook", params={"state": "in"})
        assert page.status_code == 200
        ids = {x["id"] for x in page.json()["items"]}
        assert qid in ids


@patch("app.api.practice_routes.call_doubao_grade")
def test_wrongbook_discharges_after_high_streak(mock_grade) -> None:
    with TestClient(app) as client:
        qid = _create_question(client)
        mock_grade.return_value = {"score": 3, "analysis": "bad"}
        client.post("/api/practice/daily/submit", json={"question_id": qid, "user_answer": "a"})
        assert client.get("/api/practice/wrongbook", params={"state": "in"}).json()["total"] >= 1

        mock_grade.return_value = {"score": 9, "analysis": "good"}
        for _ in range(3):
            r = client.post(
                "/api/practice/daily/submit",
                json={"question_id": qid, "user_answer": f"ans{_}"},
            )
            assert r.status_code == 200, r.text

        inn = client.get("/api/practice/wrongbook", params={"state": "in"})
        assert qid not in {x["id"] for x in inn.json()["items"]}
        out = client.get("/api/practice/wrongbook", params={"state": "out"})
        assert qid in {x["id"] for x in out.json()["items"]}


def test_wrongbook_manual_add() -> None:
    with TestClient(app) as client:
        qid = _create_question(client)
        r = client.post("/api/practice/wrongbook/manual", json={"question_id": qid})
        assert r.status_code == 200, r.text
        assert r.json()["wrongbook_active"] is True
        page = client.get("/api/practice/wrongbook", params={"state": "in"})
        assert qid in {x["id"] for x in page.json()["items"]}


@patch("app.api.practice_routes.call_doubao_grade")
def test_start_session_wrongbook_pool(mock_grade) -> None:
    mock_grade.return_value = {"score": 2, "analysis": "x"}
    cat = "wrongbook-pool-test-cat"
    with TestClient(app) as client:
        ids: list[int] = []
        for i in range(5):
            r = client.post(
                "/api/questions",
                json={
                    "stem": f"wrongbook-pool-stem-{i}-minimum-length-ok",
                    "category": cat,
                    "difficulty": 3,
                    "reference_answer": "r",
                },
            )
            assert r.status_code == 200, r.text
            qid = int(r.json()["id"])
            ids.append(qid)
            client.post(
                "/api/practice/daily/submit",
                json={"question_id": qid, "user_answer": f"x{i}"},
            )
        start = client.post(
            "/api/practice/sessions/start",
            params={"count": 5, "pool": "wrongbook", "category": cat},
        )
        assert start.status_code == 200, start.text
        got = {q["id"] for q in start.json()["questions"]}
        assert got == set(ids)
