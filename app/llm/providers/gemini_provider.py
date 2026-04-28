from __future__ import annotations

import requests

from app.config import settings
from app.llm.base_llm import BaseLLM
from app.llm.provider_utils import generate_with_retries


class GeminiProvider(BaseLLM):
    def __init__(self, temperature: float = 0.2, max_tokens: int | None = 1024):
        super().__init__(temperature=temperature, max_tokens=max_tokens)

    def _request_once(self, prompt: str, system_prompt: str | None) -> str:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")

        model = settings.GEMINI_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": self.temperature,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        if self.max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = self.max_tokens

        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])
        content = candidates[0].get("content", {}) if candidates else {}
        parts = content.get("parts", []) if isinstance(content, dict) else []
        text = parts[0].get("text", "") if parts else ""
        return self._clean_text(text)

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        return generate_with_retries(
            provider_name="gemini",
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            request_fn=self._request_once,
        )
