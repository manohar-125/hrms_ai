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

    def keyword_boost(self, query: str, tools: dict) -> list:
        """
        Keyword-based boosting for tool candidates using substring matching.
        
        Args:
            query: User query string
            tools: Dictionary of tools with keywords
        
        Returns:
            List of (tool_name, keyword_score) tuples, sorted by score descending
        """
        # Tokenize query: lowercase and split by non-alphanumeric characters
        query_tokens = re.findall(r'\b[a-z0-9]+\b', query.lower())
        query_token_set = set(query_tokens)
        
        tool_scores = []
        
        for tool_name, tool_data in tools.items():
            # Get keywords from tool data, default to empty list
            tool_keywords = tool_data.get("keywords", [])
            
            if not tool_keywords:
                tool_scores.append((tool_name, 0.0))
                continue
            
            # Convert tool keywords to lowercase for comparison
            tool_keywords_lower = [kw.lower() for kw in tool_keywords]
            
            # Calculate score using substring matching
            matching_count = 0
            for query_token in query_token_set:
                for keyword in tool_keywords_lower:
                    # Substring match: query_token in keyword or keyword in query_token
                    if query_token in keyword or keyword in query_token:
                        matching_count += 1
                        break  # Count each query token only once
            
            # Normalize score: matching_count / (total query tokens + total keywords)
            total_tokens = len(query_token_set) + len(tool_keywords_lower)
            if total_tokens > 0:
                keyword_score = matching_count / total_tokens
            else:
                keyword_score = 0.0
            
            tool_scores.append((tool_name, keyword_score))
        
        # Sort by keyword score descending
        tool_scores.sort(key=lambda x: x[1], reverse=True)
        
        return tool_scores

    def _should_filter_dashboard(self, query: str) -> bool:
        """
        Check if dashboard APIs should be filtered out.
        Only include dashboard APIs if query contains explicit dashboard keywords.
        
        Args:
            query: User query string
        
        Returns:
            True if dashboard APIs should be filtered, False otherwise
        """
        dashboard_keywords = ['dashboard', 'summary', 'analytics', 'report']
        query_lower = query.lower()
        
        for keyword in dashboard_keywords:
            if keyword in query_lower:
                return False  # Don't filter, dashboard is requested
        
        return True  # Filter out dashboard APIs

    def _filter_dashboard_apis(self, tools: list, query: str) -> list:
        """
        Remove dashboard-related APIs if not explicitly requested.
        
        Args:
            tools: List of (tool_name, score) or just tool_name strings
            query: User query string
        
        Returns:
            Filtered list with same structure as input
        """
        if not self._should_filter_dashboard(query):
            return tools  # Don't filter if dashboard is requested
        
        filtered = []
        dashboard_markers = ['dashboard', 'summary']
        
        for item in tools:
            # Handle both (tool_name, score) tuples and plain tool names
            if isinstance(item, tuple):
                tool_name = item[0]
            else:
                tool_name = item
            
            # Skip if tool name contains dashboard markers
            tool_name_lower = tool_name.lower()
            should_skip = any(marker in tool_name_lower for marker in dashboard_markers)
            
            if not should_skip:
                filtered.append(item)
        
        return filtered

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

        # Step 4 — Compute keyword scores for all filtered tools
        keyword_scores_all = self.keyword_boost(query, filtered_tools)
        keyword_score_map = {tool_name: score for tool_name, score in keyword_scores_all}
        
        print("[ToolPlanner] Keyword scores:")
        for tool_name, score in keyword_scores_all[:10]:
            if score > 0:
                print(f"  {tool_name} ({score:.4f})")

        # Step 5 — Semantic search with similarity ranking
        # Use enhanced search method that returns scores
        semantic_candidates_scored = self.vector_store.search_tools_with_scores(query, k=10)

        # Filter candidates to only include tools from domain-filtered list
        semantic_candidates_scored = [
            (tool_name, score) for tool_name, score in semantic_candidates_scored
            if tool_name in filtered_tools
        ]
        
        # Filter dashboard APIs from semantic candidates if not requested
        semantic_candidates_scored = self._filter_dashboard_apis(semantic_candidates_scored, query)

        print("[ToolPlanner] Semantic scores:")
        for tool_name, score in semantic_candidates_scored[:10]:
            print(f"  {tool_name} ({score:.4f})")

        # Step 6 — Hybrid scoring: combine semantic + keyword scores
        # final_score = semantic_score + keyword_score (as a boost)
        hybrid_scores = []
        
        for tool_name, semantic_score in semantic_candidates_scored:
            # Get keyword score for this tool, default to 0 if not available
            keyword_score = keyword_score_map.get(tool_name, 0.0)
            
            # Combine scores: semantic as primary, keyword as boost
            final_score = semantic_score + keyword_score
            
            hybrid_scores.append((tool_name, final_score, semantic_score, keyword_score))
        
        # Sort by final hybrid score descending
        hybrid_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Keep only top 3 tools for LLM decision
        final_candidates = [tool_name for tool_name, _, _, _ in hybrid_scores[:3]]
        
        print("[ToolPlanner] Hybrid ranking (semantic + keyword):")
        for tool_name, final_score, semantic_score, keyword_score in hybrid_scores[:10]:
            print(f"  {tool_name} ({final_score:.4f} = {semantic_score:.4f} + {keyword_score:.4f})")
        
        print("[ToolPlanner] Final candidates (top 3 by hybrid score):")
        for idx, tool_name in enumerate(final_candidates, 1):
            print(f"  {idx}. {tool_name}")

        # Handle fallback if no candidates found
        if not final_candidates:
            print("[ToolPlanner] No candidates found, using all domain-filtered tools")
            final_candidates = list(filtered_tools.keys())[:3]

        # Step 7 — Build tool list for LLM (using final candidates)
        tools_description = ""

        for idx, tool_name in enumerate(final_candidates, 1):
            tool_data = filtered_tools.get(tool_name)
            if not tool_data:
                continue

            description = tool_data.get("description", "")
            endpoint = tool_data.get("endpoint", "")

            tools_description += f"{idx}. Tool: {tool_name}\n   Endpoint: {endpoint}\n   Description: {description}\n\n"

        # Step 8 — Improved LLM prompt for tool selection
        prompt = f"""You are an HRMS API tool selector.

Your task: Choose the BEST API tool that directly answers the user's request.

CRITICAL RULES FOR TOOL SELECTION:

1. PREFER PRIMARY ENTITY APIs:
   - If user asks for 'employee', choose APIs that return employee records/data.
   - If user asks for 'department', choose APIs that return department data.
   - Avoid metadata, status, dashboard, or summary APIs unless explicitly requested.

2. AVOID MODIFIER/METADATA APIs:
   - Avoid APIs for status, messages, alerts, dashboards, or audits.
   - Avoid update/delete/create operations.
   - Favor GET/retrieve operations that return the main entity.

3. MATCH INTENT TO ENTITY:
   - User query intent should match the API's primary entity.
   - Example: "Show employee details" → get_employment (not get_employeestatus).

4. STRICT SELECTION:
   - Return ONLY the tool name.
   - Do NOT return explanations, reasoning, or extra text.
   - If unsure, choose the tool whose description most directly matches the user's request.

AVAILABLE TOOLS:

{tools_description}

USER QUERY:
{query}

SELECTION:

Based on the rules above, the BEST tool is:
"""

        response = generate_response(prompt)

        print(f"[ToolPlanner] LLM raw response: {response}")

        # Step 9 — Clean LLM output
        tool_name = self._clean_llm_output(response)

        print(f"[ToolPlanner] Cleaned tool name: {tool_name}")

        # Step 10 — Validate tool exists in final candidates
        if tool_name in final_candidates:
            print(f"[ToolPlanner] Final selected tool: {tool_name}")
            return tool_name, filtered_tools[tool_name]

        # Step 11 — Safe fallback to first final candidate
        print(f"[ToolPlanner] Tool '{tool_name}' not in candidates, using fallback")
        if final_candidates:
            fallback_tool = final_candidates[0]
            print(f"[ToolPlanner] Final selected tool (fallback): {fallback_tool}")
            return fallback_tool, filtered_tools[fallback_tool]

        print("[ToolPlanner] No fallback available, returning None")

        return None, None