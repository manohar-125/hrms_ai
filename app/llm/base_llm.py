from __future__ import annotations

from abc import ABC, abstractmethod
import re
import time


class BaseLLM(ABC):
    def __init__(self, temperature: float = 0.2, max_tokens: int | None = 1024):
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        raise NotImplementedError

    def _estimate_prompt_tokens(self, prompt: str, system_prompt: str | None = None) -> int:
        prompt_text = "\n".join(part for part in [system_prompt or "", prompt or ""] if part)
        if not prompt_text:
            return 0
        return max(1, len(re.findall(r"\S+", prompt_text)))

    def _clean_text(self, value: str | None) -> str:
        if not value:
            return ""

        cleaned = value.strip()
        cleaned = re.sub(r"^```(?:json|text|markdown)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip().strip('"').strip("'")
        return cleaned
