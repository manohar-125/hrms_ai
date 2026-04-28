from __future__ import annotations

import logging

import requests

from app.config import settings
from app.llm.base_llm import BaseLLM
from app.llm.provider_utils import generate_with_retries


logger = logging.getLogger(__name__)


class GroqProvider(BaseLLM):
    def __init__(self, temperature: float = 0.2, max_tokens: int | None = 1024):
        super().__init__(temperature=temperature, max_tokens=max_tokens)

    def _request_once(self, prompt: str, system_prompt: str | None) -> str:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not configured")

        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [],
            "temperature": self.temperature,
        }
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        base_url = (settings.GROQ_BASE_URL or "https://api.groq.com/openai/v1").rstrip("/")
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        choices = data.get("choices", [])
        message = choices[0].get("message", {}) if choices else {}
        text = message.get("content", "")
        return self._clean_text(text)

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        return generate_with_retries(
            provider_name="groq",
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            request_fn=self._request_once,
        )
