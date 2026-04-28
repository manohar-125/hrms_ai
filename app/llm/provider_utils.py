from __future__ import annotations

import logging
import re
import time
from typing import Callable

import requests


logger = logging.getLogger(__name__)


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
    prompt_text = "\n".join(part for part in [system_prompt or "", prompt or ""] if part)
    prompt_tokens = max(1, len(re.findall(r"\S+", prompt_text))) if prompt_text else 0
    logger.info("[LLM] Provider: %s", provider_name)
    logger.info("[LLM] Prompt tokens: %d", prompt_tokens)

    last_error: str | None = None
    attempt_count = retries + 1

    for attempt in range(1, attempt_count + 1):
        try:
            result = request_fn(prompt, system_prompt)
            response_time_ms = int((time.time() - request_start) * 1000)
            logger.info("[LLM] Response time: %d ms", response_time_ms)
            return result
        except (requests.exceptions.Timeout, requests.exceptions.RequestException, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "[LLM] Provider error: %s | attempt=%d/%d | %s",
                provider_name,
                attempt,
                attempt_count,
                last_error,
            )

    response_time_ms = int((time.time() - request_start) * 1000)
    logger.error(
        "[LLM] Provider exhausted retries: %s | error=%s",
        provider_name,
        last_error or "unknown",
    )
    logger.info("[LLM] Response time: %d ms", response_time_ms)
    raise RuntimeError(f"{provider_name} LLM failed after {attempt_count} attempts: {last_error}")
