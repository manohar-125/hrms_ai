from __future__ import annotations

import logging
import re
import time
from typing import Callable

import requests

from app.config import settings


logger = logging.getLogger(__name__)


def _get_status_code(exc: Exception) -> int | None:
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None)


def _get_retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    retry_after = headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        return float(retry_after)
    except (TypeError, ValueError):
        return None


def _truncate_prompt(prompt: str, max_tokens: int | None) -> str:
    if not prompt or not max_tokens:
        return prompt
    words = re.findall(r"\S+", prompt)
    if len(words) <= max_tokens:
        return prompt
    trimmed = " ".join(words[-max_tokens:])
    return trimmed


def generate_with_retries(
    provider_name: str,
    prompt: str,
    system_prompt: str | None,
    temperature: float,
    max_tokens: int | None,
    request_fn: Callable[[str, str | None], str],
    retries: int = 2,
) -> str:
    request_start = time.time()
    prompt_limit = settings.LLM_MAX_PROMPT_TOKENS
    prompt = _truncate_prompt(prompt, prompt_limit)
    prompt_text = "\n".join(part for part in [system_prompt or "", prompt or ""] if part)
    prompt_tokens = max(1, len(re.findall(r"\S+", prompt_text))) if prompt_text else 0
    logger.info("[LLM] Provider: %s", provider_name)
    logger.info("[LLM] Prompt tokens: %d", prompt_tokens)

    last_error: str | None = None
    attempt_count = retries + 1

    for attempt in range(1, attempt_count + 1):
        try:
            logger.info("[LLM REQUEST] provider=%s", provider_name)
            result = request_fn(prompt, system_prompt)
            response_time_ms = int((time.time() - request_start) * 1000)
            logger.info("[LLM] Response time: %d ms", response_time_ms)
            return result
        except (requests.exceptions.Timeout, requests.exceptions.RequestException, ValueError) as exc:
            last_error = str(exc)
            status_code = _get_status_code(exc)
            logger.warning(
                "[LLM] Provider error: %s | attempt=%d/%d | %s",
                provider_name,
                attempt,
                attempt_count,
                last_error,
            )

            if attempt < attempt_count:
                retry_after = _get_retry_after_seconds(exc)
                if retry_after is not None:
                    backoff_seconds = max(0.0, retry_after)
                else:
                    backoff_seconds = min(8.0, 1.0 * (2 ** (attempt - 1)))

                if status_code in {429, 500, 502, 503, 504} or retry_after is not None:
                    logger.info(
                        "[LLM] Backoff %.2fs before retry (status=%s)",
                        backoff_seconds,
                        status_code,
                    )
                    time.sleep(backoff_seconds)

    response_time_ms = int((time.time() - request_start) * 1000)
    logger.error(
        "[LLM] Provider exhausted retries: %s | error=%s",
        provider_name,
        last_error or "unknown",
    )
    logger.info("[LLM] Response time: %d ms", response_time_ms)
    raise RuntimeError(f"{provider_name} LLM failed after {attempt_count} attempts: {last_error}")
