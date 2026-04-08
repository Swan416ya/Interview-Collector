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
                    chunks: list[str] = []
                    for part in content:
                        if isinstance(part, dict):
                            text = part.get("text")
                            if isinstance(text, str) and text.strip():
                                chunks.append(text)
                    if chunks:
                        return "\n".join(chunks)

    # 4) Give caller a structured preview in error path
    return ""


def call_doubao_extract(prompt: str, raw_text: str, thinking_type: str | None = None) -> tuple[dict, dict]:
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

    url = f"{settings.ai_base_url.rstrip('/')}/responses"
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.ai_model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": raw_text}]},
        ],
        # Limit output size to reduce long-tail latency on extraction.
        "max_output_tokens": settings.ai_max_output_tokens,
        "temperature": 0,
        # Ark Responses API supports disabling deep thinking via this field.
        "thinking": {"type": thinking_type or settings.ai_thinking_type},
    }

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
            "AI request start attempt=%s model=%s base_url=%s raw_text_len=%s",
            attempt + 1,
            settings.ai_model,
            settings.ai_base_url,
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


def call_doubao_grade(question_stem: str, user_answer: str) -> dict:
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
    result, _ = call_doubao_extract(prompt=prompt, raw_text=input_text, thinking_type="disabled")
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

