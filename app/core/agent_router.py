import logging
import re
import json
from difflib import SequenceMatcher
from app.core.tool_planner import ToolPlanner
from app.core.tool_executor import ToolExecutor
from app.core.entity_extractor import extract_entities
from app.core.tool_validator import ToolValidator
from app.llm.llm_factory import get_llm
from app.cache.redis_cache import RedisCache

logger = logging.getLogger(__name__)

# Initialize components
planner = ToolPlanner()
executor = ToolExecutor()
validator = ToolValidator(planner.registry)
cache = RedisCache()


def _normalize_text(value: str) -> str:
    value = value or ""
    value = re.sub(r"[^a-zA-Z0-9\s]", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def _extract_rows(api_response):
    if isinstance(api_response, list):
        return api_response
    if isinstance(api_response, dict):
        data = api_response.get("data")
        if isinstance(data, list):
            return data
    return None


def _filter_rows_by_employee_name(rows: list, employee_name: str):
    if not rows or not employee_name:
        return rows

    target = _normalize_text(employee_name)
    target_tokens = set(target.split())

    scored = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        full_name = str(row.get("fullName", ""))
        norm_name = _normalize_text(full_name)
        if not norm_name:
            continue

        row_tokens = set(norm_name.split())
        token_overlap = len(target_tokens & row_tokens)
        ratio = SequenceMatcher(None, target, norm_name).ratio()
        active_bonus = 0.2 if row.get("isActive") is True else 0.0

        score = token_overlap + ratio + active_bonus
        scored.append((score, row))

    if not scored:
        return rows

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_row = scored[0]

    # Require at least one overlapping token for confident name match.
    if best_score <= 0 or not (target_tokens & set(_normalize_text(str(best_row.get("fullName", ""))).split())):
        return rows

    return [best_row]


def route_query(intent: str, question: str, return_source: bool = False):

    try:

        # Step 0️⃣ Check cache first
        cached = cache.get(question)

        if cached:
            logger.info(f"Agent Cache HIT")
            if return_source:
                # Return cached answer without source (will be added by RAG engine)
                return cached, None
            return cached
        
        logger.info(f"Agent Cache MISS")

        # Step 1️⃣ Find appropriate tool
        tool_name, tool_data = planner.find_tool(question)

        if not tool_name:
            if return_source:
                return "Sorry, I could not find a suitable HRMS API for this query.", None
            return "Sorry, I could not find a suitable HRMS API for this query."

        # Step 2️⃣ Validate tool
        # Keep validator in sync with planner's latest in-memory registry.
        validator.registry = planner.registry
        is_valid, result = validator.validate(tool_name)

        if not is_valid:
            error_msg = f"Tool validation failed: {result}"
            if return_source:
                return error_msg, None
            return error_msg

        tool_data = result

        # Step 3️⃣ Extract entities
        entities = extract_entities(question)

        endpoint = tool_data["endpoint"]

        if "id" in entities:
            endpoint = endpoint.replace("{id}", str(entities["id"]))

        updated_tool_data = tool_data.copy()
        updated_tool_data["endpoint"] = endpoint

        # Step 4️⃣ Execute API
        api_response = executor.execute(updated_tool_data)

        # Step 4.1️⃣ For name-based queries, narrow list payloads to the best employee match.
        employee_name = entities.get("employee_name")
        rows = _extract_rows(api_response)
        if employee_name and isinstance(rows, list):
            filtered_rows = _filter_rows_by_employee_name(rows, employee_name)
            if filtered_rows is not rows:
                if isinstance(api_response, list):
                    api_response = filtered_rows
                elif isinstance(api_response, dict) and isinstance(api_response.get("data"), list):
                    api_response = {**api_response, "data": filtered_rows}

        # Step 5️⃣ Generate final answer from raw API response
        llm = get_llm()
        final_answer = llm.generate(
            f"""
    You are an HRMS assistant.

    User question:
    {question}

    HRMS API response (JSON):
{json.dumps(api_response, indent=2)}

    Instructions:
    - Convert the API response into a clear natural language answer.
    - If it is a list, format it nicely.
    - If data is empty, say no data found.
    - Do not explain JSON.
    - Only return the final answer.

    Answer:
    """
        )

        # Step 7️⃣ Store result in cache
        cache.set(question, final_answer)

        # Extract source metadata
        api_source = {
            "source_type": "api",
            "method": updated_tool_data.get("method", "GET"),
            "endpoint": updated_tool_data.get("endpoint", ""),
        }

        if return_source:
            return final_answer, api_source
        return final_answer

    except Exception as e:
        error_msg = f"Error executing query: {str(e)}"
        if return_source:
            return error_msg, None
        return error_msg