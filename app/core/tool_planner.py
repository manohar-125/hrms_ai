import json
from pathlib import Path
from app.llm.llama_client import generate_response
from app.core.domain_classifier import classify_domain


class ToolPlanner:

    def __init__(self):

        registry_path = Path("app/tools/api_registry.json")

        with open(registry_path, "r") as f:
            self.registry = json.load(f)

    def find_tool(self, query: str):

        # Step 1 — Detect domain
        domain = classify_domain(query)

        print(f"[ToolPlanner] Detected domain: {domain}")

        # Step 2 — Filter tools by domain
        filtered_tools = {}

        for tool_name, tool_data in self.registry.items():

            if tool_data.get("domain") == domain:
                filtered_tools[tool_name] = tool_data

        # fallback if domain not found
        if not filtered_tools:

            print("[ToolPlanner] No domain match, using full registry")
            filtered_tools = self.registry

        # Step 3 — Prefer APIs without parameters
        clean_tools = {}

        for name, data in filtered_tools.items():

            endpoint = data.get("endpoint", "")

            if "{" not in endpoint:
                clean_tools[name] = data

        # if we found clean APIs, use them
        if clean_tools:
            filtered_tools = clean_tools

        print(f"[ToolPlanner] Tools available: {len(filtered_tools)}")

        # Step 4 — Build tool list for LLM
        tools_description = ""

        for tool_name, tool_data in filtered_tools.items():

            description = tool_data.get("description", "")
            endpoint = tool_data.get("endpoint", "")

            tools_description += f"{tool_name} | {endpoint} | {description}\n"

        prompt = f"""
You are an HRMS API planner.

Select the BEST API tool for the user query.

Available tools:
{tools_description}

User Query:
{query}

Rules:
- Return ONLY the tool name
- Do NOT explain anything
- If no tool matches return NONE

Tool:
"""

        response = generate_response(prompt).strip()

        # extract first token (in case LLM adds explanation)
        tool_name = response.split()[0].strip()

        print(f"[ToolPlanner] LLM raw response: {response}")
        print(f"[ToolPlanner] Parsed tool: {tool_name}")

        if tool_name == "NONE":
            return None, None

        if tool_name in filtered_tools:
            return tool_name, filtered_tools[tool_name]

        print("[ToolPlanner] Tool not found in filtered list")

        return None, None