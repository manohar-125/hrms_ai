import logging
from app.core.query_router import route
from app.core.agent_router import route_query
from app.core.policy_service import get_policy_context
from app.core.context_builder import add_to_context, build_context_prompt
from app.llm.llama_client import generate_response
from app.llm.prompts import SYSTEM_PROMPT
from app.cache.redis_cache import RedisCache

logger = logging.getLogger(__name__)
cache = RedisCache()


def _format_source_attribution(source_meta: dict | None) -> str:
    """
    Format source metadata into a user-friendly attribution string.
    
    Args:
        source_meta: dict with source_type and additional fields
        
    Returns:
        Formatted source attribution string, or empty string if no metadata
    """
    if not source_meta:
        return ""
    
    source_type = source_meta.get("source_type")
    
    if source_type == "policy":
        name = source_meta.get("name", "Company Policy")
        page = source_meta.get("page_number")
        if page:
            return f"\nSource: {name} (Page {page})"
        else:
            return f"\nSource: {name}"
    
    elif source_type == "api":
        method = source_meta.get("method", "GET")
        endpoint = source_meta.get("endpoint", "")
        if endpoint:
            return f"\nSource: {method} {endpoint}"
        else:
            return f"\nSource: {method} API"
    
    return ""


def answer_question(question: str, session_id: str = "default", return_source: bool = False):

    # Step 0️⃣ Cache check
    cache_key = f"rag:{session_id}:{question}"

    cached = cache.get(cache_key)

    if cached:
        logger.info(f"RAG Cache HIT")
        if return_source:
            # For cached results, we don't have source metadata available
            return cached, None
        return cached
    
    logger.info(f"RAG Cache MISS")
    
    # Step 1️⃣ build conversation context
    conversation_context = build_context_prompt(session_id)

    route_type = route(question)
    logger.info(f"Query route: {route_type}")

    # POLICY → RAG pipeline
    if route_type == "policy":

        retrieved_data = get_policy_context(question, return_source=True)
        documents, source_meta = retrieved_data

        context = "\n".join(documents)

        prompt = f"""
{SYSTEM_PROMPT}

Conversation History:
{conversation_context}

Context:
{context}

Question:
{question}

Answer:
"""

        answer = generate_response(prompt)

        add_to_context(session_id, question, answer)

        # Step 2️⃣ store in cache
        cache.set(cache_key, answer)

        if return_source:
            return answer, source_meta
        return answer

    # DATA → HRMS Tool Agent
    retrieved_data = route_query("data", question, return_source=True)
    
    if return_source:
        answer, source_meta = retrieved_data
    else:
        answer = retrieved_data
        source_meta = None

    add_to_context(session_id, question, answer)

    # Step 3️⃣ store in cache
    cache.set(cache_key, answer)

    if return_source:
        return answer, source_meta
    return answer