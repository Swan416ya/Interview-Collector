import json
import logging
import re
import time
from collections.abc import Iterator

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.services.ai_connect import prepare_https_url_with_doh

logger = logging.getLogger(__name__)


def _hint_ai_transport_error(message: str) -> str:
    """为 DNS/代理类失败补充可操作的简短说明（面向 NDJSON error 与 502 detail）。"""
    lower = message.lower()
    if any(
        x in lower
        for x in (
            "getaddrinfo",
            "11001",
            "name or service not known",
            "temporary failure in name resolution",
            "nodename nor servname",
        )
    ):
        return (
            f"{message} | 说明：无法解析 API 域名或经代理解析失败。请检查本机网络；用 nslookup 测 "
            f"AI_BASE_URL 的主机名；若环境变量里配置了 HTTP_PROXY/HTTPS_PROXY，可在 backend/.env 设 "
            f"AI_HTTP_TRUST_ENV=false 让 AI 直连；已默认开启 AI_DOH_FALLBACK（通过 1.1.1.1/8.8.8.8/223.5.5.5 "
            f"的 DoH 取 IP 再连），若仍失败请换网络或设 AI_DOH_FALLBACK=false 后排查防火墙是否拦截上述 IP 的 HTTPS。"
        )
    return message


GRADE_SYSTEM_PROMPT = """
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


def call_llm_json(
    system_prompt: str,
    user_text: str,
    *,
    op: str,
    max_output_tokens: int | None = None,
    thinking_type: str | None = None,
) -> tuple[dict, dict]:
    """
    Thin entry for all JSON-returning LLM calls (extract, grade, kb_query, session_summary, etc.).
    Shares timeout, retries, and logging with `_post_doubao_responses_op`.
    """
    return _post_doubao_responses_op(
        system_prompt,
        user_text,
        op=op,
        max_output_tokens=max_output_tokens,
        thinking_type=thinking_type,
    )


def _post_doubao_responses_op(
    prompt: str,
    raw_text: str,
    *,
    op: str,
    max_output_tokens: int | None = None,
    thinking_type: str | None = None,
) -> tuple[dict, dict]:
    """Ark /responses or OpenAI-compatible /chat/completions (e.g. Xiaomi MiMo Token Plan)."""
    wall_start = time.perf_counter()

    def _wall_ms() -> int:
        return int((time.perf_counter() - wall_start) * 1000)

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
        logger.info(
            "ai_call_done op=%s outcome=unsupported_provider latency_ms=%s",
            op,
            _wall_ms(),
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unsupported AI_PROVIDER",
                "ai_provider": settings.ai_provider,
                "hint": "Use ark_responses or openai_compatible",
            },
        )

    url, doh_ext, doh_headers = prepare_https_url_with_doh(url)
    send_headers = {**headers, **doh_headers}
    httpx_extensions = doh_ext or None

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
            with httpx.Client(timeout=timeout, trust_env=settings.ai_http_trust_env) as client:
                resp = client.post(
                    url,
                    headers=send_headers,
                    json=payload,
                    extensions=httpx_extensions,
                )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info("AI response status=%s elapsed_ms=%s", resp.status_code, elapsed_ms)
            if resp.status_code >= 400:
                body_preview = _safe_text_preview(resp.text)
                logger.error("AI bad status body=%s", body_preview)
                logger.info(
                    "ai_call_done op=%s outcome=http_error latency_ms=%s provider=%s "
                    "http_status=%s attempt=%s",
                    op,
                    _wall_ms(),
                    provider,
                    resp.status_code,
                    attempt + 1,
                )
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
            logger.info(
                "ai_call_done op=%s outcome=transport_error latency_ms=%s provider=%s attempts=%s error=%s",
                op,
                _wall_ms(),
                provider,
                settings.ai_retries + 1,
                last_error,
            )
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "AI request failed after retries",
                    "error": _hint_ai_transport_error(last_error),
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
        logger.info(
            "ai_call_done op=%s outcome=no_response latency_ms=%s provider=%s",
            op,
            _wall_ms(),
            provider,
        )
        raise HTTPException(status_code=502, detail={"message": "AI request got empty response"})

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        body_preview = _safe_text_preview(resp.text)
        logger.error("AI response not JSON body=%s", body_preview)
        logger.info(
            "ai_call_done op=%s outcome=invalid_json_body latency_ms=%s provider=%s http_status=%s",
            op,
            _wall_ms(),
            provider,
            resp.status_code,
        )
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
        logger.info(
            "ai_call_done op=%s outcome=no_output_text latency_ms=%s provider=%s http_status=%s",
            op,
            _wall_ms(),
            provider,
            resp.status_code,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "message": "AI response has no parseable output text",
                "response_preview": preview,
            },
        )
    try:
        parsed = _extract_json_object(output_text)
    except HTTPException:
        logger.info(
            "ai_call_done op=%s outcome=output_json_parse_error latency_ms=%s provider=%s http_status=%s",
            op,
            _wall_ms(),
            provider,
            resp.status_code,
        )
        raise
    logger.info(
        "ai_call_done op=%s outcome=ok latency_ms=%s provider=%s http_status=%s model=%s",
        op,
        _wall_ms(),
        provider,
        resp.status_code,
        settings.ai_model,
    )
    return parsed, data


def call_doubao_extract(prompt: str, raw_text: str) -> tuple[dict, dict]:
    return call_llm_json(
        prompt,
        raw_text,
        op="extract",
        max_output_tokens=settings.ai_max_output_tokens,
        thinking_type="disabled",
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
    parsed, _ = call_llm_json(
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
    parsed, _ = call_llm_json(
        SESSION_SUMMARY_SYSTEM_PROMPT,
        session_digest,
        op="session_summary",
        max_output_tokens=settings.ai_session_summary_max_output_tokens,
        thinking_type="disabled",
    )
    return parsed


def _finalize_grading_dict(result: dict) -> dict:
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


def _grading_dict_from_assistant_text(output_text: str) -> dict:
    """Parse streamed (or non-streamed) assistant text into {score, analysis}."""
    try:
        raw = _extract_json_object(output_text)
        return _finalize_grading_dict(raw)
    except HTTPException as exc:
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


def call_doubao_grade(question_stem: str, user_answer: str) -> dict:
    input_text = f"题目：{question_stem}\n用户回答：{user_answer}"
    try:
        result, _ = call_llm_json(
            GRADE_SYSTEM_PROMPT,
            input_text,
            op="grade",
            max_output_tokens=settings.ai_max_output_tokens,
            thinking_type="disabled",
        )
    except HTTPException as exc:
        detail = getattr(exc, "detail", None)
        if isinstance(detail, dict) and detail.get("message") == "Failed to parse AI JSON output":
            preview = str(detail.get("output_preview", ""))
            return _grading_dict_from_assistant_text(preview)
        raise
    return _finalize_grading_dict(result)


def _grade_user_payload(question_stem: str, user_answer: str) -> str:
    return f"题目：{question_stem}\n用户回答：{user_answer}"


def iter_grade_stream_events(question_stem: str, user_answer: str) -> Iterator[tuple[str, str | dict]]:
    """
    For NDJSON practice grading streams.

    Yields:
      ("reasoning", delta) — model chain-of-thought chunk (MiMo OpenAI stream: reasoning_content)
      ("graded", {"score": int, "analysis": str})
      ("error", message) — terminal; no further events
    """
    provider = _normalize_ai_provider()
    user_text = _grade_user_payload(question_stem, user_answer)

    if provider != "openai_compatible":
        yield ("reasoning", "正在阅卷…\n")
        try:
            g = call_doubao_grade(question_stem, user_answer)
        except HTTPException as exc:
            detail = getattr(exc, "detail", None)
            msg = json.dumps(detail, ensure_ascii=False) if detail is not None else str(exc)
            yield ("error", msg)
            return
        yield ("graded", g)
        return

    if not settings.ai_api_key or not settings.ai_model:
        yield ("error", "AI config missing (AI_API_KEY / AI_MODEL)")
        return

    base = settings.ai_base_url.rstrip("/")
    url = f"{base}/chat/completions"
    tokens = settings.ai_max_output_tokens
    payload = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": GRADE_SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0,
        "stream": True,
        "max_tokens": tokens,
        "max_completion_tokens": tokens,
    }
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
    }
    url, doh_ext, doh_headers = prepare_https_url_with_doh(url)
    send_headers = {**headers, **doh_headers}
    httpx_extensions = doh_ext or None

    timeout = httpx.Timeout(
        timeout=settings.ai_timeout_seconds,
        connect=settings.ai_connect_timeout_seconds,
        read=settings.ai_read_timeout_seconds,
    )
    # 禁用连接池 keep-alive，降低部分网络/代理下 TLS 流式读一半被对端重置的概率。
    _ai_limits = httpx.Limits(max_keepalive_connections=0, max_connections=100)

    content_parts: list[str] = []

    for attempt in range(settings.ai_retries + 1):
        stream_made_progress = False
        content_parts.clear()
        try:
            # 每次请求新建 Transport，避免 Client 关闭后复用已关闭的底层连接池。
            transport = httpx.HTTPTransport(retries=0, http2=False)
            with httpx.Client(
                timeout=timeout,
                limits=_ai_limits,
                transport=transport,
                trust_env=settings.ai_http_trust_env,
            ) as client:
                with client.stream(
                    "POST",
                    url,
                    headers=send_headers,
                    json=payload,
                    extensions=httpx_extensions,
                ) as resp:
                    if resp.status_code >= 400:
                        body = resp.read().decode("utf-8", errors="replace")[:800]
                        yield ("error", f"AI stream HTTP {resp.status_code}: {body}")
                        return
                    for line in resp.iter_lines():
                        if not line or line.startswith(":"):
                            continue
                        if not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            obj = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        choices = obj.get("choices")
                        if not isinstance(choices, list) or not choices:
                            continue
                        delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
                        if not isinstance(delta, dict):
                            continue
                        rc = delta.get("reasoning_content")
                        if isinstance(rc, str) and rc:
                            yield ("reasoning", rc)
                            stream_made_progress = True
                        else:
                            alt_r = delta.get("reasoning")
                            if isinstance(alt_r, str) and alt_r:
                                yield ("reasoning", alt_r)
                                stream_made_progress = True
                        piece = delta.get("content")
                        if isinstance(piece, str) and piece:
                            content_parts.append(piece)
                            stream_made_progress = True
            break
        except httpx.HTTPError as exc:
            err_msg = str(exc)
            logger.warning(
                "AI stream transport failed attempt=%s/%s progress=%s error=%s",
                attempt + 1,
                settings.ai_retries + 1,
                stream_made_progress,
                err_msg,
            )
            if stream_made_progress or attempt >= settings.ai_retries:
                yield ("error", _hint_ai_transport_error(f"AI stream transport error: {err_msg}"))
                return
            time.sleep(1.5 * (attempt + 1))
            continue

    full_text = "".join(content_parts).strip()
    if not full_text:
        yield ("error", "AI stream ended with empty assistant content")
        return
    try:
        graded = _grading_dict_from_assistant_text(full_text)
    except HTTPException as exc:
        detail = getattr(exc, "detail", None)
        msg = json.dumps(detail, ensure_ascii=False) if isinstance(detail, (dict, list)) else str(detail or exc)
        yield ("error", msg)
        return
    yield ("graded", graded)


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
    result, _ = call_llm_json(
        prompt,
        f"题目：{question_stem}",
        op="reference_answer",
        max_output_tokens=settings.ai_max_output_tokens,
        thinking_type="disabled",
    )
    answer = str(result.get("reference_answer", "")).strip()
    return answer

