import logging

from app.cache.redis_cache import get_cache, normalize_query, set_cache, should_skip_cache
from app.llm.llm_factory import get_llm


VALID_INTENTS = {
    "employee", "department", "attendance", "leave", "payroll",
    "project", "task", "client", "policy", "general"
}


logger = logging.getLogger(__name__)


INTENT_PROMPT = """
You are an intent classifier for an HRMS AI assistant.

Your task: Classify the user question into exactly ONE intent category.

Available intents (choose only one):
- employee (queries about employee records, information, profiles)
- department (queries about departments, organization structure)
- attendance (queries about attendance, time tracking, check-in)
- leave (queries about leaves, balances, policies)
- payroll (queries about salary, compensation, payroll processing)
- project (queries about projects, assignments, tracking)
- task (queries about tasks, work items)
- client (queries about clients, relationships)
- policy (queries about HR policies, guidelines, rules)
- general (other queries, unrelated to specific categories)

Classification Rules:
1. Return ONLY the intent name in lowercase.
2. Do NOT include explanations or reasoning.
3. If multiple intents match, choose the PRIMARY intent.
4. Be strict and precise in your classification.

Examples:

Question: Show all departments
Intent: department

Question: List employees in HR
Intent: employee

Question: What is the leave policy
Intent: policy

Question: Check my attendance record
Intent: attendance

Question: Show project details
Intent: project

Now classify this question:

Question:
{question}

Intent:
"""


def classify_intent(question: str):
    normalized_query = normalize_query(question)
    cache_key = f"intent:{normalized_query}"
    cache_skipped = should_skip_cache(question)

    if not cache_skipped:
        cached = get_cache(cache_key)
        if isinstance(cached, dict):
            cached_intent = (cached.get("intent") or "").strip().lower()
            if cached_intent in VALID_INTENTS:
                logger.info("[CACHE HIT] intent:%s", normalized_query)
                return cached_intent
        logger.info("[CACHE MISS] intent:%s", normalized_query)

    prompt = INTENT_PROMPT.format(question=question)

    llm = get_llm()
    response = llm.generate(prompt)
    normalized = response.strip().lower()

    # Handle occasional prefixes/suffixes from LLM output.
    if "intent:" in normalized:
        normalized = normalized.split("intent:")[-1].strip()

    normalized = normalized.split()[0].strip(".,:;!?\"'()[]{}") if normalized else ""

    if normalized in VALID_INTENTS:
        if not cache_skipped:
            set_cache(cache_key, {"intent": normalized}, ttl=3600)
        return normalized

    if not cache_skipped:
        set_cache(cache_key, {"intent": "general"}, ttl=3600)
    return "general"