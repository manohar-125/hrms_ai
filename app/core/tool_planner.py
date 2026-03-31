import json
import re
import logging
from pathlib import Path

from app.llm.llama_client import generate_response
from app.config import settings

logger = logging.getLogger(__name__)

from app.core.domain_classifier import classify_domain
from app.vectordb.api_vector_store import APIVectorStore


EMPPERSDTLS_TOOL = "get_emppersdtls"


class ToolPlanner:

    def __init__(self):

        self.registry_path = Path("app/tools/api_registry.json")
        self.registry = {}
        self._load_registry()

        # semantic search store
        self.vector_store = APIVectorStore()

    def _load_registry(self):

        with open(self.registry_path, "r") as f:
            self.registry = json.load(f)

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

    def _filter_metadata_apis(self, tools: list, query: str) -> list:
        """
        Deprioritize metadata/type/status APIs unless explicitly requested.
        These are less useful for general queries.
        
        Args:
            tools: List of (tool_name, score) tuples
            query: User query string
        
        Returns:
            Filtered list with metadata APIs removed/downscored
        """
        metadata_keywords = ['type', 'status', 'config', 'setting', 'category']
        query_lower = query.lower()
        
        # Don't filter if query explicitly asks for metadata
        if any(kw in query_lower for kw in metadata_keywords):
            return tools  # Keep all if metadata is requested
        
        filtered = []
        for tool_name, score in tools:
            tool_name_lower = tool_name.lower()
            # Heavily penalize metadata APIs by removing them (not just downscoring)
            if not any(marker in tool_name_lower for marker in metadata_keywords):
                filtered.append((tool_name, score))
        
        return filtered if filtered else tools  # Return original if all filtered

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

    def _prefer_personal_details_tool(self, query: str, filtered_tools: dict):
        """
        Prefer personal-details API for employee contact/profile questions.
        This avoids selecting unrelated employee sub-resources (bank, task, etc.)
        when users ask for mobile/email/contact-type attributes.
        """
        query_lower = query.lower()

        personal_terms = [
            "mobile", "phone", "contact", "email", "mail", "dob",
            "gender", "blood", "marital", "father", "husband", "personal"
        ]
        employee_terms = ["employee", "employees", "emp"]
        bank_terms = ["bank", "account", "ifsc", "salary", "payroll", "pay"]

        asks_personal = any(term in query_lower for term in personal_terms)
        has_employee_context = any(term in query_lower for term in employee_terms)
        asks_bank_or_pay = any(term in query_lower for term in bank_terms)

        if asks_personal and has_employee_context and not asks_bank_or_pay:
            if EMPPERSDTLS_TOOL in filtered_tools:
                return EMPPERSDTLS_TOOL, filtered_tools[EMPPERSDTLS_TOOL]

        return None, None

    def _prefer_employment_for_list_queries(self, query: str, filtered_tools: dict):
        """
        For unspecific "show all employees" queries, prefer get_employment
        to avoid semantic confusion with task/expense/timesheet tools.
        """
        query_lower = query.lower()

        list_keywords = ["show", "list", "all", "display", "get", "fetch", "names"]
        employee_keywords = ["employee", "employees", "emp", "staff", "member", "members"]

        asks_list = any(kw in query_lower for kw in list_keywords)
        asks_employee = any(kw in query_lower for kw in employee_keywords)

        has_specific_attr = any(kw in query_lower for kw in [
            "task", "timesheet", "expense", "bank", "family", "education", "certificate",
            "salary", "payroll", "leave", "attendance"
        ])

        if asks_list and asks_employee and not has_specific_attr:
            if "get_employment" in filtered_tools:
                return "get_employment", filtered_tools["get_employment"]

        return None, None

    def find_tool(self, query: str):

        # Reload registry on each request so add/remove changes are picked up
        # without restarting the API service.
        self._load_registry()

        # Step 1 — Detect domain
        domain = classify_domain(query)

        # Step 2 — Filter tools by domain
        filtered_tools = {}

        for tool_name, tool_data in self.registry.items():

            if tool_data.get("domain") == domain:
                filtered_tools[tool_name] = tool_data

        # fallback if domain not found
        if not filtered_tools:
            filtered_tools = self.registry

        # Step 3 — Prefer APIs without parameters when query doesn't request ID-style lookup
        query_lower = query.lower()
        id_focused_query = bool(re.search(r"\b\d+\b", query_lower)) or bool(re.search(r"\bid\b", query_lower))
        clean_tools = {}

        for name, data in filtered_tools.items():

            endpoint = data.get("endpoint", "")

            if "{" not in endpoint:
                clean_tools[name] = data

        if clean_tools and not id_focused_query:
            filtered_tools = clean_tools

        # Step 3.1 — Short-circuit for known personal-details intents.
        preferred_name, preferred_data = self._prefer_personal_details_tool(query, filtered_tools)
        if preferred_name:
            logger.info(f"Rule-selected personal details tool: {preferred_name}")
            return preferred_name, preferred_data

        # Step 3.2 — Short-circuit for generic employee-list queries.
        preferred_name, preferred_data = self._prefer_employment_for_list_queries(query, filtered_tools)
        if preferred_name:
            logger.info(f"Rule-selected employment tool for list: {preferred_name}")
            return preferred_name, preferred_data

        # Step 4 — Compute keyword scores for all filtered tools
        keyword_scores_all = self.keyword_boost(query, filtered_tools)
        keyword_score_map = {tool_name: score for tool_name, score in keyword_scores_all}

        # Step 5 — Semantic search with similarity ranking
        # Use enhanced search method that returns scores
        semantic_candidates_scored = self.vector_store.search_tools_with_scores(query, k=settings.SEMANTIC_SEARCH_K)

        # Filter candidates to only include tools from domain-filtered list
        semantic_candidates_scored = [
            (tool_name, score) for tool_name, score in semantic_candidates_scored
            if tool_name in filtered_tools
        ]
        
        # Filter dashboard APIs from semantic candidates if not requested
        semantic_candidates_scored = self._filter_dashboard_apis(semantic_candidates_scored, query)

        # Filter metadata/type/status APIs unless explicitly requested
        semantic_candidates_scored = self._filter_metadata_apis(semantic_candidates_scored, query)

        # Step 6 — Hybrid scoring: combine semantic + keyword scores
        # final_score = semantic_score + keyword_score (as a boost)
        hybrid_scores = []
        
        for tool_name, semantic_score in semantic_candidates_scored:
            # Get keyword score for this tool, default to 0 if not available
            keyword_score = keyword_score_map.get(tool_name, 0.0)
            
            # Combine scores: semantic as primary, keyword as boost
            final_score = semantic_score + (keyword_score * settings.KEYWORD_WEIGHT)
            
            hybrid_scores.append((tool_name, final_score, semantic_score, keyword_score))
        
        # Sort by final hybrid score descending
        hybrid_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Filter to only top scoring tools (at least configured similarity threshold)
        threshold_candidates = [(name, score, sem_score) for name, score, sem_score, _ in hybrid_scores if score >= settings.SIMILARITY_THRESHOLD]
        
        if not threshold_candidates:
            # Fallback: use top 1 if no tools meet threshold
            threshold_candidates = [(hybrid_scores[0][0], hybrid_scores[0][1], hybrid_scores[0][2])] if hybrid_scores else []
        
        # HIGH CONFIDENCE SELECTION: Smart selection with strict criteria
        if settings.REQUIRE_HIGH_CONFIDENCE and threshold_candidates and len(threshold_candidates) >= 1:
            top_name, top_score, top_sem_score = threshold_candidates[0]
            
            # Confidence check: needs both high score AND clear winner status
            second_score = threshold_candidates[1][1] if len(threshold_candidates) > 1 else 0
            score_margin = top_score - second_score
            
            # STRICT: needs very high confidence OR clear margin over competitors
            high_confidence = top_sem_score >= 0.7  # Very high semantic match (70%+)
            clear_winner = score_margin >= 0.15  # At least 15% margin over second place
            
            if (high_confidence or clear_winner) and top_sem_score >= 0.6:
                tool_data = filtered_tools.get(top_name)
                tool_desc = tool_data.get("description", "").lower() if tool_data else ""
                
                # Verify tool description matches query intent
                query_lower = query.lower()
                if any(word in tool_desc for word in query_lower.split()):
                    logger.info(f"Auto-selected (high confidence): {top_name} (score: {top_sem_score:.3f}, margin: {score_margin:.3f})")
                    if tool_data:
                        return top_name, tool_data
        
        # Use best single candidate (no LLM needed if only one)
        if len(threshold_candidates) == 1:
            final_candidates = [threshold_candidates[0][0]]
        else:
            # Only consult LLM if there are multiple candidates with similar scores
            final_candidates = [name for name, _, _ in threshold_candidates[:3]]

        # Step 7 — Build tool list for LLM (using final candidates)
        tools_description = ""

        for idx, tool_name in enumerate(final_candidates, 1):
            tool_data = filtered_tools.get(tool_name)
            if not tool_data:
                continue

            description = tool_data.get("description", "")
            endpoint = tool_data.get("endpoint", "")

            tools_description += f"{idx}. Tool: {tool_name}\n   Endpoint: {endpoint}\n   Description: {description}\n\n"

        logger.info(f"LLM candidates: {final_candidates}")

        # Step 8 — Only use LLM if multiple candidates exist
        if len(final_candidates) > 1:
            prompt = f"""You are an HRMS API selector. Select the BEST API.

RULES:
1. PREFER: APIs returning data/records (get_*, retrieve, list, info) 
2. AVOID: Type/Status/Config/Metadata APIs
3. MATCH: Primary entity over secondary (employee > type/status)
4. EXCLUDE: Dashboard, Report, Summary unless explicitly requested

TOOLS:
{tools_description}

QUERY: {query}

Return ONLY the tool name, nothing else."""

            response = generate_response(prompt)
            tool_name = self._clean_llm_output(response)

            logger.info(f"LLM selected: {tool_name}")

            # Validate tool exists in final candidates
            if tool_name in final_candidates:
                return tool_name, filtered_tools[tool_name]

            # Safe fallback to first final candidate
            if final_candidates:
                fallback_tool = final_candidates[0]
                logger.info(f"LLM selection '{tool_name}' invalid, fallback: {fallback_tool}")
                return fallback_tool, filtered_tools[fallback_tool]
        else:
            # Single candidate - use it directly
            if final_candidates:
                tool_name = final_candidates[0]
                logger.info(f"Single candidate: {tool_name}")
                return tool_name, filtered_tools[tool_name]

        return None, None