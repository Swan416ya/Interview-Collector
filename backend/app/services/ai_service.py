import json
import logging
import re
import time

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


def _safe_text_preview(text: str, limit: int = 400) -> str:
    cleaned = text.replace("\n", " ").replace("\r", " ")
    return cleaned[:limit]


def _extract_json_object(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            logger.error("AI output is not JSON. preview=%s", _safe_text_preview(text))
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "AI response is not valid JSON",
                    "output_preview": _safe_text_preview(text),
                },
            )
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            logger.error("AI JSON parse failed: %s", str(exc))
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "Failed to parse AI JSON output",
                    "parse_error": str(exc),
                    "output_preview": _safe_text_preview(match.group(0)),
                },
            ) from exc


def _normalize_ai_provider() -> str:
    p = (settings.ai_provider or "ark_responses").strip().lower()
    if p in ("ark", "ark_responses", "volcengine", "doubao"):
        return "ark_responses"
    if p in ("openai", "openai_compatible", "openai-compat", "compatible"):
        return "openai_compatible"
    return p


def _extract_output_text_from_response(data: dict) -> str:
    # 1) Preferred shortcut if provider gives flattened output_text
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    # 2) Ark/OpenAI responses style: output[].content[].text
    output = data.get("output")
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        chunks.append(text)
            # Some providers may place text directly
            text_direct = item.get("text")
            if isinstance(text_direct, str) and text_direct.strip():
                chunks.append(text_direct)
        if chunks:
            return "\n".join(chunks)

    # 3) Chat completions compatible fallback: choices[0].message.content
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content
                if isinstance(content, list):
                    chunks_msg: list[str] = []
                    for part in content:
                        if isinstance(part, dict):
                            text = part.get("text")
                            if isinstance(text, str) and text.strip():
                                chunks_msg.append(text)
                    if chunks_msg:
                        return "\n".join(chunks_msg)
                rc = message.get("reasoning_content")
                if isinstance(rc, str) and rc.strip():
                    return rc

    # 4) Give caller a structured preview in error path
    return ""


def _post_doubao_responses_op(
    prompt: str,
    raw_text: str,
    *,
    op: str,
    max_output_tokens: int | None = None,
    thinking_type: str | None = None,
) -> tuple[dict, dict]:
    """Ark /responses or OpenAI-compatible /chat/completions (e.g. Xiaomi MiMo Token Plan)."""
    if not settings.ai_api_key or not settings.ai_model:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "AI config missing",
                "missing": [
                    key
                    for key, value in {
                        "AI_API_KEY": settings.ai_api_key,
                        "AI_MODEL": settings.ai_model,
                    }.items()
                    if not value
                ],
            },
        )

    provider = _normalize_ai_provider()
    base = settings.ai_base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
    }
    tokens = max_output_tokens if max_output_tokens is not None else settings.ai_max_output_tokens

    if provider == "openai_compatible":
        url = f"{base}/chat/completions"
        payload = {
            "model": settings.ai_model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": raw_text},
            ],
            "max_tokens": tokens,
            "temperature": 0,
        }
        logger.info(
            "ai_call_prepare op=%s provider=openai_compatible prompt_len=%s user_text_len=%s max_tokens=%s",
            op,
            len(prompt),
            len(raw_text),
            tokens,
        )
    elif provider == "ark_responses":
        url = f"{base}/responses"
        payload = {
            "model": settings.ai_model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": raw_text}]},
            ],
            "max_output_tokens": tokens,
            "temperature": 0,
            "thinking": {"type": thinking_type or settings.ai_thinking_type},
        }
        logger.info(
            "ai_call_prepare op=%s provider=ark_responses prompt_len=%s user_text_len=%s thinking=%s max_out=%s",
            op,
            len(prompt),
            len(raw_text),
            thinking_type or settings.ai_thinking_type,
            tokens,
        )
    else:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unsupported AI_PROVIDER",
                "ai_provider": settings.ai_provider,
                "hint": "Use ark_responses or openai_compatible",
            },
        )

    timeout = httpx.Timeout(
        timeout=settings.ai_timeout_seconds,
        connect=settings.ai_connect_timeout_seconds,
        read=settings.ai_read_timeout_seconds,
    )
    last_error: str | None = None
    resp: httpx.Response | None = None

    for attempt in range(settings.ai_retries + 1):
        started = time.perf_counter()
        logger.info(
            "ai_call_start op=%s attempt=%s provider=%s model=%s base_url=%s prompt_len=%s user_text_len=%s",
            op,
            attempt + 1,
            provider,
            settings.ai_model,
            settings.ai_base_url,
            len(prompt),
            len(raw_text),
        )
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info("AI response status=%s elapsed_ms=%s", resp.status_code, elapsed_ms)
            if resp.status_code >= 400:
                body_preview = _safe_text_preview(resp.text)
                logger.error("AI bad status body=%s", body_preview)
                raise HTTPException(
                    status_code=502,
                    detail={
                        "message": "AI provider returned error status",
                        "status_code": resp.status_code,
                        "response_preview": body_preview,
                        "elapsed_ms": elapsed_ms,
                        "attempt": attempt + 1,
                        "model": settings.ai_model,
                        "base_url": settings.ai_base_url,
                    },
                )
            break
        except HTTPException:
            raise
        except httpx.HTTPError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            last_error = str(exc)
            logger.warning(
                "AI request failed attempt=%s elapsed_ms=%s error=%s",
                attempt + 1,
                elapsed_ms,
                last_error,
            )
            if attempt < settings.ai_retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "AI request failed after retries",
                    "error": last_error,
                    "attempts": settings.ai_retries + 1,
                    "model": settings.ai_model,
                    "base_url": settings.ai_base_url,
                    "timeout": {
                        "connect_s": settings.ai_connect_timeout_seconds,
                        "read_s": settings.ai_read_timeout_seconds,
                    },
                },
            ) from exc

    if resp is None:
        raise HTTPException(status_code=502, detail={"message": "AI request got empty response"})

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        body_preview = _safe_text_preview(resp.text)
        logger.error("AI response not JSON body=%s", body_preview)
        raise HTTPException(
            status_code=502,
            detail={
                "message": "AI response body is not JSON",
                "error": str(exc),
                "response_preview": body_preview,
            },
        ) from exc

    if settings.ai_debug_raw_response:
        logger.info("AI raw response full=%s", json.dumps(data, ensure_ascii=False))

    output_text = _extract_output_text_from_response(data)
    if not output_text:
        preview = _safe_text_preview(json.dumps(data, ensure_ascii=False), 800)
        logger.error("AI response has no parseable output text. body=%s", preview)
        raise HTTPException(
            status_code=502,
            detail={
                "message": "AI response has no parseable output text",
                "response_preview": preview,
            },
        )
    parsed = _extract_json_object(output_text)
    return parsed, data


def call_doubao_extract(prompt: str, raw_text: str, thinking_type: str | None = None) -> tuple[dict, dict]:
    return _post_doubao_responses_op(
        prompt,
        raw_text,
        op="responses_extract",
        max_output_tokens=settings.ai_max_output_tokens,
        thinking_type=thinking_type,
    )


KB_QUERY_SYSTEM_PROMPT = """
你是面试题知识库助手。你只能根据 user JSON 里 fragments 数组中的文本作答。
规则：
1) 若 fragments 为空、或其中没有任何与用户问题相关的信息，则 answer 必须且仅为：知识库中未找到相关条目（不要加引号或其它字）
2) 否则只依据 fragments 综合回答；可使用 Markdown；禁止编造 fragments 中不存在的技术细节、数字或公司名。
3) 只输出 JSON，不要任何解释文字。
4) cited_chunk_ids 中的每个整数必须是 fragments 里出现过的 chunk_id；禁止编造 id。
5) 输出格式：
{
  "answer": "string",
  "cited_chunk_ids": [1, 2]
}
""".strip()


def call_doubao_kb_query(user_question: str, fragments: list[dict]) -> dict:
    payload = {"user_question": user_question, "fragments": fragments}
    raw = json.dumps(payload, ensure_ascii=False)
    parsed, _ = _post_doubao_responses_op(
        KB_QUERY_SYSTEM_PROMPT,
        raw,
        op="kb_query",
        max_output_tokens=settings.ai_kb_max_output_tokens,
        thinking_type="disabled",
    )
    return parsed


SESSION_SUMMARY_SYSTEM_PROMPT = """
你是计算机面试刷题会话总评助手。用户刚完成一轮固定题量的作答（每题已有 0-10 的得分与简短解析）。请根据下方逐题摘要给出本轮整体评价。
规则：
1) 只输出 JSON，不要任何解释文字。
2) summary_text：中文总评，不超过 280 字，可含 Markdown 列表；指出主要薄弱点与巩固建议。
3) dimensions：恰好 **5** 个维度，每个含 key（英文蛇形，唯一）、label（中文 2–6 字）、score（0-10 整数）。建议五维为：正确性、完整性、表达清晰度、知识深度、临场稳定性（可按作答表现微调分数，不必与单题均分机械一致）。
4) 输出格式：
{
  "summary_text": "string",
  "dimensions": [
    {"key": "correctness", "label": "正确性", "score": 7},
    {"key": "completeness", "label": "完整性", "score": 6},
    {"key": "articulation", "label": "表达力", "score": 7},
    {"key": "depth", "label": "知识深度", "score": 5},
    {"key": "consistency", "label": "稳定性", "score": 6}
  ]
}
""".strip()


def call_doubao_session_summary(session_digest: str) -> dict:
    """One-shot session-level feedback; returns parsed JSON dict."""
    parsed, _ = _post_doubao_responses_op(
        SESSION_SUMMARY_SYSTEM_PROMPT,
        session_digest,
        op="session_summary",
        max_output_tokens=settings.ai_session_summary_max_output_tokens,
        thinking_type="disabled",
    )
    return parsed


def call_doubao_grade(question_stem: str, user_answer: str) -> dict:
    logger.info(
        "ai_call_prepare op=grade stem_len=%s answer_len=%s",
        len(question_stem),
        len(user_answer),
    )
    prompt = """
你是计算机面试官。请对用户回答打分并给出解析。
规则：
1) 只输出 JSON，不要任何解释文字。
2) score 为 0-10 的整数。
3) analysis 是针对本次回答的解析，必须小于 200 字。
4) 输出格式必须为：
{
  "score": 0,
  "analysis": "string"
}
""".strip()
    input_text = f"题目：{question_stem}\n用户回答：{user_answer}"
    try:
        result, _ = call_doubao_extract(prompt=prompt, raw_text=input_text, thinking_type="disabled")
    except HTTPException as exc:
        # Grading path fallback:
        # Some model outputs are almost-JSON but contain unescaped quotes inside analysis,
        # causing strict JSON parse failure. Try to salvage score/analysis from preview text.
        detail = getattr(exc, "detail", None)
        if isinstance(detail, dict) and detail.get("message") == "Failed to parse AI JSON output":
            preview = str(detail.get("output_preview", ""))
            score_match = re.search(r'"score"\s*:\s*(-?\d+)', preview)
            analysis_match = re.search(r'"analysis"\s*:\s*"([\s\S]*)"\s*\}\s*$', preview)
            if score_match and analysis_match:
                score = int(score_match.group(1))
                analysis = analysis_match.group(1).strip()
                if len(analysis) > 200:
                    analysis = analysis[:200]
                score = max(0, min(10, score))
                logger.warning("AI grading parsed via fallback regex due to invalid JSON output")
                return {"score": score, "analysis": analysis}
        raise

    if "score" not in result or "analysis" not in result:
        raise HTTPException(status_code=502, detail="AI grading output missing score or analysis")
    try:
        score = int(result["score"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="AI grading score must be int") from exc
    score = max(0, min(10, score))
    analysis = str(result.get("analysis", "")).strip()
    if len(analysis) > 200:
        analysis = analysis[:200]
    return {"score": score, "analysis": analysis}


def call_doubao_reference_answer(question_stem: str) -> str:
    logger.info("ai_call_prepare op=reference_answer stem_len=%s", len(question_stem))
    prompt = """
你是计算机面试题参考答案生成器。
规则：
1) 只输出 JSON，不要任何解释文字。
2) 输出格式：
{
  "reference_answer": "string"
}
3) reference_answer 直接给清晰、准确、可用于复习的答案。
""".strip()
    result, _ = call_doubao_extract(prompt=prompt, raw_text=f"题目：{question_stem}", thinking_type="disabled")
    answer = str(result.get("reference_answer", "")).strip()
    return answer

