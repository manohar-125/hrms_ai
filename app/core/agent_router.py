import logging
from app.core.tool_planner import ToolPlanner
from app.core.tool_executor import ToolExecutor
from app.core.entity_extractor import extract_entities
from app.core.tool_validator import ToolValidator
from app.llm.llama_client import generate_answer
from app.llm.response_parser import parse_api_response
from app.cache.redis_cache import RedisCache

logger = logging.getLogger(__name__)

# Initialize components
planner = ToolPlanner()
executor = ToolExecutor()
validator = ToolValidator(planner.registry)
cache = RedisCache()


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

        # Step 5️⃣ Parse API response
        parsed_response = parse_api_response(api_response)

        # Step 6️⃣ Generate final answer
        final_answer = generate_answer(question, parsed_response)

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