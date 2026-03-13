from app.core.query_router import route
from app.core.agent_router import route_query
from app.core.policy_service import get_policy_context
from app.core.context_builder import add_to_context, build_context_prompt
from app.llm.llama_client import generate_response
from app.llm.prompts import SYSTEM_PROMPT
from app.cache.redis_cache import RedisCache


cache = RedisCache()


def answer_question(question: str, session_id: str = "default"):

    # Step 0️⃣ Cache check
    cache_key = f"rag:{question}"

    cached = cache.get(cache_key)

    if cached:
        print("RAG Cache HIT")
        return cached

    print("RAG Cache MISS")

    # Step 1️⃣ build conversation context
    conversation_context = build_context_prompt(session_id)

    route_type = route(question)

    print("Query route:", route_type)

    # POLICY → RAG pipeline
    if route_type == "policy":

        documents = get_policy_context(question)

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

        return answer

    # DATA → HRMS Tool Agent
    answer = route_query("data", question)

    add_to_context(session_id, question, answer)

    # Step 3️⃣ store in cache
    cache.set(cache_key, answer)

    return answer