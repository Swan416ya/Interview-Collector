from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_kb_query_empty_corpus_returns_not_found() -> None:
    with TestClient(app) as client:
        res = client.post("/api/kb/query", json={"query": "no-such-content-xyz-12345"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["answer"] == "知识库中未找到相关条目"
    assert body["citations"] == []


@patch("app.api.kb_routes.call_doubao_kb_query")
def test_kb_query_returns_answer_and_citations(mock_kb) -> None:
    def _fake(user_q: str, fragments: list[dict]) -> dict:
        cid = fragments[0]["chunk_id"]
        return {"answer": "基于片段的简要说明。", "cited_chunk_ids": [cid]}

    mock_kb.side_effect = _fake

    with TestClient(app) as client:
        cr = client.post(
            "/api/questions",
            json={
                "stem": "唯一标识符 Redis 持久化 RDB 与 AOF 区别",
                "category": "未分类",
                "difficulty": 3,
                "reference_answer": "RDB 快照，AOF 追加日志。",
            },
        )
        assert cr.status_code == 200, cr.text
        res = client.post("/api/kb/query", json={"query": "Redis 持久化", "top_k": 5})
    assert res.status_code == 200, res.text
    body = res.json()
    assert "说明" in body["answer"]
    assert len(body["citations"]) >= 1
    assert body["citations"][0]["question_id"] == cr.json()["id"]
    assert body["citations"][0]["source_type"] in ("question_stem", "question_reference")


def test_kb_reindex_processes_existing_question() -> None:
    with TestClient(app) as client:
        cr = client.post(
            "/api/questions",
            json={
                "stem": "reindex-test-stem-alpha",
                "category": "未分类",
                "difficulty": 2,
                "reference_answer": "reindex-test-ref-beta",
            },
        )
        assert cr.status_code == 200, cr.text
        rr = client.post("/api/kb/reindex")
    assert rr.status_code == 200, rr.text
    assert rr.json()["questions_processed"] >= 1
