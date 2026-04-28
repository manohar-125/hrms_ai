from __future__ import annotations

import requests

from app.config import settings
from app.llm.base_llm import BaseLLM
from app.llm.provider_utils import generate_with_retries


class AnthropicProvider(BaseLLM):
    def __init__(self, temperature: float = 0.2, max_tokens: int | None = 1024):
        super().__init__(temperature=temperature, max_tokens=max_tokens)

    def _request_once(self, prompt: str, system_prompt: str | None) -> str:
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

        payload = {
            "model": settings.ANTHROPIC_MODEL,
            "max_tokens": self.max_tokens or 1024,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        content = data.get("content", [])
        if content and isinstance(content, list):
            text = content[0].get("text", "")
        else:
            text = ""
        return self._clean_text(text)

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        return generate_with_retries(
            provider_name="anthropic",
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            request_fn=self._request_once,
        )
