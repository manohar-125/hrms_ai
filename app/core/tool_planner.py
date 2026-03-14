import json
import re
from pathlib import Path

from app.llm.llama_client import generate_response
from app.core.domain_classifier import classify_domain
from app.vectordb.api_vector_store import APIVectorStore


class ToolPlanner:

    def __init__(self):

        registry_path = Path("app/tools/api_registry.json")

        with open(registry_path, "r") as f:
            self.registry = json.load(f)

        # semantic search store
        self.vector_store = APIVectorStore()

    def _clean_llm_output(self, response: str) -> str:
        """
        Clean LLM output to extract just the tool name.
        Handles various formats like:
        - "Tool: get_employment"
        - "The best tool is get_employment"
        - "get_employment"
        - "1. get_employment"
        """
        # Remove common prefixes
        cleaned = response.strip()
        
        # Remove patterns like "Tool:", "Tool is:", "The best tool is:", etc.
        cleaned = re.sub(r'^(Tool|The best tool|Selected tool)[:\s]+', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^[\d\.\)]+\s*', '', cleaned)  # Remove numbering like "1. " or "1) "
        
        # Extract the first word (tool name should not have spaces)
        tool_name = cleaned.split()[0] if cleaned else ""
        
        # Remove any trailing punctuation
        tool_name = re.sub(r'[:\.,;\'"]*$', '', tool_name)
        
        return tool_name.strip()

    def _compute_fallback_tool(self, ranked_candidates: list) -> tuple:
        """
        Return the highest similarity tool as fallback.
        Returns (tool_name, tool_data) tuple.
        """
        if not ranked_candidates:
            return None, None
        
        # ranked_candidates is sorted by score descending, so first is highest
        best_tool_name, best_score = ranked_candidates[0]
        
        if best_tool_name in self.registry:
            return best_tool_name, self.registry[best_tool_name]
        
        return None, None

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

        if clean_tools:
            filtered_tools = clean_tools

        print(f"[ToolPlanner] Tools after domain filter: {len(filtered_tools)}")

        # Step 4 — Semantic search with similarity ranking
        # Use enhanced search method that returns scores
        candidates_with_scores = self.vector_store.search_tools_with_scores(query, k=10)

        # Filter candidates to only include tools from domain-filtered list
        ranked_candidates = []
        
        for tool_name, score in candidates_with_scores:
            if tool_name in filtered_tools:
                ranked_candidates.append((tool_name, score))

        # Keep only top 3 most similar tools
        ranked_candidates = ranked_candidates[:3]

        # Handle fallback if semantic filter fails
        if not ranked_candidates:
            print("[ToolPlanner] No semantic candidates found, using all domain-filtered tools")
            # Create dummy scores for fallback tools
            ranked_candidates = [(name, 0.5) for name in list(filtered_tools.keys())[:3]]

        # Log similarity ranking
        print("[ToolPlanner] Similarity ranking:")
        for tool_name, score in ranked_candidates:
            print(f"  {tool_name} ({score:.2f})")

        # Step 5 — Build tool list for LLM (using ranked candidates)
        tools_description = ""

        for idx, (tool_name, score) in enumerate(ranked_candidates, 1):
            tool_data = filtered_tools.get(tool_name)
            if not tool_data:
                continue

            description = tool_data.get("description", "")
            endpoint = tool_data.get("endpoint", "")

            tools_description += f"{idx}. {tool_name}\n   endpoint: {endpoint}\n   description: {description}\n\n"

        # Step 6 — Improved LLM prompt for tool selection
        prompt = f"""You are an HRMS API planner.

Select the BEST API tool for the user query.

Available tools:
{tools_description}

User Query:
{query}

Rules:
- Return ONLY the tool name
- Do NOT explain or add extra text
- If no tool matches exactly, choose the closest match
- Return just the tool name, nothing else

Selected Tool:"""

        response = generate_response(prompt)

        print(f"[ToolPlanner] LLM raw response: {response}")

        # Step 7 — Clean LLM output
        tool_name = self._clean_llm_output(response)

        print(f"[ToolPlanner] Cleaned tool name: {tool_name}")

        # Step 8 — Validate tool exists in ranked candidates
        ranked_tool_names = [name for name, _ in ranked_candidates]
        
        if tool_name in ranked_tool_names:
            print(f"[ToolPlanner] Final selected tool: {tool_name}")
            return tool_name, filtered_tools[tool_name]

        # Step 9 — Safe fallback to highest similarity tool
        print(f"[ToolPlanner] Tool '{tool_name}' not in candidates, using fallback")
        fallback_tool, fallback_data = self._compute_fallback_tool(ranked_candidates)
        
        if fallback_tool:
            print(f"[ToolPlanner] Final selected tool (fallback): {fallback_tool}")
            return fallback_tool, fallback_data

        print("[ToolPlanner] No fallback available, returning None")

        return None, None