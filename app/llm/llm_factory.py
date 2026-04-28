from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.llm.providers.anthropic_provider import AnthropicProvider
from app.llm.providers.gemini_provider import GeminiProvider
from app.llm.providers.groq_provider import GroqProvider
from app.llm.providers.openai_provider import OpenAIProvider


@lru_cache(maxsize=1)
def get_llm():
    provider = (settings.LLM_PROVIDER or "openai").strip().lower()

    if provider == "openai":
        return OpenAIProvider()
    if provider == "groq":
        return GroqProvider()
    if provider == "anthropic":
        return AnthropicProvider()
    if provider == "gemini":
        return GeminiProvider()

    return OpenAIProvider()
