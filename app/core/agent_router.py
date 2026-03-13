from app.core.tool_planner import ToolPlanner
from app.core.tool_executor import ToolExecutor
from app.core.entity_extractor import extract_entities
from app.core.tool_validator import ToolValidator
from app.llm.llama_client import generate_answer
from app.llm.response_parser import parse_api_response
from app.cache.redis_cache import RedisCache


# Initialize components
planner = ToolPlanner()
executor = ToolExecutor()
validator = ToolValidator(planner.registry)
cache = RedisCache()


def route_query(intent: str, question: str):

    try:

        # Step 0️⃣ Check cache first
        cached = cache.get(question)

        if cached:
            print("Cache HIT")
            return cached

        print("Cache MISS")

        # Step 1️⃣ Find appropriate tool
        tool_name, tool_data = planner.find_tool(question)

        if not tool_name:
            return "Sorry, I could not find a suitable HRMS API for this query."

        # Step 2️⃣ Validate tool
        is_valid, result = validator.validate(tool_name)

        if not is_valid:
            return f"Tool validation failed: {result}"

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

        return final_answer

    except Exception as e:
        return f"Error executing query: {str(e)}"