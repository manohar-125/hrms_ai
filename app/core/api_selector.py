"""
Advanced API Selector with Hybrid Matching, Intent Filtering, and Confidence Scoring.

This module implements a sophisticated API selection algorithm that:
- Uses hybrid scoring (semantic + keyword + intent)
- Performs intent-based filtering
- Re-ranks top candidates
- Provides confidence scores
- Includes fallback mechanisms for low confidence
- Filters list queries to prefer non-_id variants
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

from app.config import settings
from app.core.intent_classifier import classify_intent
from app.core.domain_classifier import classify_domain
from app.core.entity_extractor import extract_employee_name, detect_requested_attribute
from app.vectordb.api_vector_store import APIVectorStore

logger = logging.getLogger(__name__)


# Stopwords to remove during query normalization
STOPWORDS = {
    "the", "a", "an", "and", "or", "is", "are", "am", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "must", "can",
    "in", "on", "at", "to", "from", "of", "for", "with", "by", "about",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "up", "down", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "what", "which",
    "my", "me", "i", "you", "he", "she", "it", "we", "they"
}

# Synonym mappings for query expansion
SYNONYMS = {
    "list": ["show", "get", "display", "retrieve", "fetch"],
    "all": ["every", "list"],
    "details": ["detail", "info", "information", "profile"],
    "emp": ["employee"],
    "emps": ["employee"],
    "sal": ["salary"],
    "dept": ["department"],
    "depts": ["department"],
    "attn": ["attendance"],
    "proj": ["project"],
    "projs": ["project"],
    "phone": ["mobile", "contact"],
    "mail": ["email"],
}

PARTIAL_MATCH_MIN = 0.6
WEAK_PARTIAL_PENALTY = 0.05
EXACT_KEYWORD_BOOST = 0.15
PARAM_MISSING_PENALTY = 0.3
LOW_CONFIDENCE_BLOCK = 0.6

EMPPERSDTLS_TOOL = "get_emppersdtls"


class APISelector:
    """Advanced API selector with hybrid matching and fallback handling."""

    def __init__(self):
        """Initialize the API selector."""
        self.registry = {}
        self.vector_store = APIVectorStore()
        self.last_reasons: Dict[str, List[str]] = {}
        self.load_registry()

    def load_registry(self):
        """Load API registry from JSON file."""
        registry_path = Path("app/tools/api_registry.json")
        with open(registry_path, "r") as f:
            self.registry = json.load(f)

    def set_registry(self, registry: Dict):
        """Set registry directly (used for runtime session registries)."""
        self.registry = registry or {}

    def set_vector_store(self, vector_store: APIVectorStore):
        """Set vector store directly (used for runtime session collections)."""
        self.vector_store = vector_store

    def normalize_query(self, query: str) -> Tuple[str, List[str]]:
        """Normalize user query and expand synonyms."""
        query_lower = query.lower()
        tokens = re.findall(r'\b[a-z0-9]+\b', query_lower)
        filtered_tokens = [t for t in tokens if t not in STOPWORDS]
        
        expanded_tokens = []
        for token in filtered_tokens:
            expanded_tokens.append(token)
            for canonical, variants in SYNONYMS.items():
                if token == canonical:
                    expanded_tokens.extend(variants)
                elif token in variants:
                    expanded_tokens.append(canonical)
        
        # Preserve order while removing duplicates.
        seen = set()
        deduped_tokens = []
        for token in expanded_tokens:
            if token not in seen:
                deduped_tokens.append(token)
                seen.add(token)

        normalized_query = " ".join(filtered_tokens)
        return normalized_query, deduped_tokens

    def fuzzy_match(self, query_token: str, keyword: str, threshold: float = PARTIAL_MATCH_MIN) -> float:
        """Fuzzy match between query token and API keyword."""
        if query_token == keyword:
            return 1.0
        if query_token in keyword or keyword in query_token:
            return 0.9
        
        ratio = SequenceMatcher(None, query_token, keyword).ratio()
        return ratio if ratio >= threshold else 0.0

    def calculate_keyword_score(self, query: str, api_name: str, keywords: List[str], description: str) -> float:
        """Calculate keyword matching score."""
        normalized_query, expanded_tokens = self.normalize_query(query)
        query_tokens_set = set(expanded_tokens)
        
        if not query_tokens_set:
            return 0.0
        
        matching_score = 0.0
        exact_match_hits = 0
        weak_partial_hits = 0

        keyword_tokens = set()
        for keyword in keywords:
            keyword_tokens.update(re.findall(r"\b[a-z0-9]+\b", keyword.lower()))
        
        for q_token in query_tokens_set:
            best_match = 0.0
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                match_score = self.fuzzy_match(q_token, keyword_lower, threshold=PARTIAL_MATCH_MIN)
                best_match = max(best_match, match_score)
            
            api_name_lower = api_name.lower()
            if "_" in api_name_lower:
                name_parts = api_name_lower.split("_")
                for part in name_parts:
                    match_score = self.fuzzy_match(q_token, part, threshold=PARTIAL_MATCH_MIN)
                    best_match = max(best_match, match_score)

            if q_token in keyword_tokens:
                exact_match_hits += 1
            elif 0.0 < best_match < 0.75:
                weak_partial_hits += 1
            
            matching_score += best_match
        
        keyword_score = matching_score / len(query_tokens_set)
        if exact_match_hits:
            keyword_score += min(0.3, (exact_match_hits / len(query_tokens_set)) * EXACT_KEYWORD_BOOST)
        if weak_partial_hits:
            keyword_score -= min(0.2, weak_partial_hits * WEAK_PARTIAL_PENALTY)
        return min(1.0, keyword_score)

    def calculate_intent_score(self, query: str, api_normalized_intent: Optional[str]) -> float:
        """Calculate intent matching score."""
        if not api_normalized_intent:
            return 0.0
        
        query_intent = classify_intent(query)
        api_intent_lower = str(api_normalized_intent).lower()
        query_intent_lower = query_intent.lower()
        
        if query_intent_lower in api_intent_lower or api_intent_lower in query_intent_lower:
            return 1.0
        
        domain = classify_domain(query)
        if domain and domain in api_intent_lower:
            return 0.8
        
        return 0.0

    def re_rank_candidates(
        self,
        query: str,
        candidates: List[Tuple[str, float]],
        semantic_scores: Dict[str, float],
        top_k: int = 5
    ) -> List[Tuple[str, float, float, float, float]]:
        """Re-rank top candidates using hybrid scoring plus EmpPersDtls priority boosts."""
        # Pre-filter: Remove _id variants if query asks for list/all
        list_keywords = ["all", "list", "show all", "display", "retrieve all", "get all"]
        query_lower = query.lower()
        is_list_query = any(kw in query_lower for kw in list_keywords)
        detected_attribute = detect_requested_attribute(query)
        employee_name = extract_employee_name(query)
        conflicting_domain = any(keyword in query_lower for keyword in ["salary", "payroll", "bank", "leave"])
        has_details_signal = any(keyword in query_lower for keyword in ["details", "detail", "info", "information", "profile"])
        has_employee_context = any(keyword in query_lower for keyword in ["employee", "employees", "emp"])
        has_personal_list_signal = any(keyword in query_lower for keyword in ["name", "mobile", "phone", "contact", "email", "blood", "dob", "gender", "religion", "marital", "father", "husband"])
        has_numeric_id = bool(re.search(r"\b\d+\b", query))
        has_id_term = bool(re.search(r"\bid\b", query_lower))
        has_id_focus = has_numeric_id or has_id_term
        has_task_signal = any(keyword in query_lower for keyword in ["task", "timesheet", "work item", "worklog"])
        has_status_signal = "status" in query_lower
        is_bank_query = any(keyword in query_lower for keyword in ["bank", "account", "ifsc"])
        is_salary_query = any(keyword in query_lower for keyword in ["salary", "pay", "earning", "deduction", "payroll"])
        is_employee_query = has_employee_context and not is_bank_query and not is_salary_query
        is_generic_employee_query = is_employee_query and any(
            keyword in query_lower for keyword in ["information", "info", "details", "profile", "employee information"]
        )
        has_analytical_salary_signal = is_salary_query and any(
            keyword in query_lower for keyword in ["highest", "top", "maximum", "lowest", "minimum"]
        )
        entities = {
            "id": bool(re.search(r"\b\d+\b", query_lower)),
            "employee_name": bool(extract_employee_name(query)),
            "requested_attribute": bool(detected_attribute),
        }
        no_entities = not any(entities.values())
        strong_personal_signal = bool(detected_attribute or employee_name or has_details_signal)
        personal_list_query = bool(is_list_query and has_employee_context and (detected_attribute or has_personal_list_signal))

        # Ensure EmpPersDtls participates in ranking when personal-detail signal is strong.
        if (strong_personal_signal or personal_list_query) and not conflicting_domain and EMPPERSDTLS_TOOL in self.registry:
            emppers_exists = any(name == EMPPERSDTLS_TOOL for name, _ in candidates)
            if not emppers_exists:
                candidates = [(EMPPERSDTLS_TOOL, semantic_scores.get(EMPPERSDTLS_TOOL, 0.0))] + candidates
            else:
                # Move it to front so it is always evaluated within top_k.
                candidates = [
                    (name, score) for name, score in candidates if name != EMPPERSDTLS_TOOL
                ]
                candidates = [(EMPPERSDTLS_TOOL, semantic_scores.get(EMPPERSDTLS_TOOL, 0.0))] + candidates
        
        filtered_candidates = candidates
        if is_list_query:
            # Query asks for list - filter out _id/_by_id variants
            filtered_candidates = [
                (name, score) for name, score in candidates
                if "_id" not in name.lower() and "_by_id" not in name.lower()
            ]
            if filtered_candidates:
                candidates = filtered_candidates
                logger.info(f"List filter applied: removed _id variants for '{query}'")
        
        re_ranked = []
        self.last_reasons = {}
        
        for tool_name, _ in candidates[:top_k]:
            if tool_name not in self.registry:
                continue
            
            tool_data = self.registry[tool_name]
            reasons: List[str] = []
            semantic_score = semantic_scores.get(tool_name, 0.0)
            
            keyword_score = self.calculate_keyword_score(
                query,
                tool_name,
                tool_data.get("keywords", []),
                tool_data.get("description", "")
            )
            
            intent_score = self.calculate_intent_score(
                query,
                tool_data.get("normalized_intent")
            )
            
            # Hybrid score: 0.5 semantic + 0.3 keyword + 0.2 intent
            final_score = (
                settings.SEMANTIC_WEIGHT * semantic_score +
                settings.KEYWORD_WEIGHT * keyword_score +
                settings.INTENT_WEIGHT * intent_score
            )

            tool_data = self.registry.get(tool_name, {})
            endpoint = str(tool_data.get("endpoint", "")).lower()
            requires_params = "{" in endpoint and "}" in endpoint
            is_id_api = ("_id" in tool_name.lower() or "{id}" in endpoint)
            tool_name_lower = tool_name.lower()
            is_task_api = any(marker in tool_name_lower for marker in ["task", "timesheet"])
            is_bank_api = any(marker in tool_name_lower for marker in ["bank", "empbankaccount"])
            is_salary_api = any(marker in tool_name_lower for marker in ["salary", "payroll", "earning", "deduction"])
            is_employee_core_api = any(
                marker in tool_name_lower for marker in ["emppersdtls", "employment", "empfamily", "empidentity"]
            )

            # Penalize id-based APIs when query has no explicit numeric id.
            if not has_numeric_id and not has_id_term and is_id_api:
                final_score -= 0.35
                reasons.append("penalty:no_explicit_id")

            # Critical reliability rule: avoid required-param APIs when entities are absent.
            if requires_params and no_entities:
                final_score -= PARAM_MISSING_PENALTY
                reasons.append("penalty:required_params_missing_entities")

            # If user explicitly asks for id, prioritize id endpoints.
            if has_id_term and is_id_api:
                final_score += 0.25
                reasons.append("boost:explicit_id_query")
            elif has_id_term and not is_id_api:
                final_score -= 0.10
                reasons.append("penalty:id_query_non_id_endpoint")

            # Generic/vague queries should prefer safe list endpoints.
            if no_entities and not has_id_focus:
                if not requires_params:
                    final_score += 0.1
                    reasons.append("boost:safe_no_required_params")
                if any(token in endpoint for token in ["/list", "/all"]) or "list" in tool_name_lower:
                    final_score += 0.08
                    reasons.append("boost:list_endpoint_for_generic_query")
                if is_id_api:
                    final_score -= 0.15
                    reasons.append("penalty:id_endpoint_for_generic_query")

            # Status signal should prefer likely filter/list endpoints over details-by-id.
            if has_status_signal and requires_params:
                final_score -= 0.08
                reasons.append("penalty:status_query_with_required_params")

            # Strict blocking inside employee domain: generic employee queries must avoid task APIs.
            if is_employee_query and not has_task_signal and is_task_api:
                final_score -= 0.65
                reasons.append("penalty:task_api_for_employee_query")

            # Generic employee information should map to EmpPersDtls/Employment.
            if is_generic_employee_query and is_employee_core_api:
                final_score += 0.30
                reasons.append("boost:generic_employee_info_match")
            if "employee information" in query_lower and "emppersdtls" in tool_name_lower:
                final_score += 0.50
                reasons.append("boost:employee_information_exact_signal")

            # Employee by id should prioritize correct employee APIs with id endpoints.
            if is_employee_query and has_id_focus and not has_task_signal:
                if is_employee_core_api and is_id_api:
                    final_score += 0.35
                    reasons.append("boost:employee_id_query_match")
                if "employment" in tool_name_lower or "emppersdtls" in tool_name_lower:
                    final_score += 0.20
                    reasons.append("boost:employee_core_api")
                if is_task_api:
                    final_score -= 0.70
                    reasons.append("penalty:task_api_for_employee_id_query")

            # Bank/account queries should force bank APIs and block task APIs.
            if is_bank_query:
                if is_bank_api:
                    final_score += 0.60
                    reasons.append("boost:bank_query_bank_api")
                if is_task_api:
                    final_score -= 0.80
                    reasons.append("penalty:task_api_for_bank_query")
                if not is_bank_api and is_employee_core_api:
                    final_score -= 0.15
                    reasons.append("penalty:employee_core_api_for_bank_query")

            # Salary queries should prioritize salary/payroll APIs and avoid task APIs.
            if is_salary_query:
                if is_salary_api:
                    final_score += 0.35
                    reasons.append("boost:salary_query_salary_api")
                if is_task_api:
                    final_score -= 0.75
                    reasons.append("penalty:task_api_for_salary_query")
                if has_analytical_salary_signal and "salary" in tool_name_lower:
                    final_score += 0.20
                    reasons.append("boost:analytical_salary_signal")

            # Priority boost layer for EmpPersDtls without forcing selection.
            is_emppersdtls = "emppersdtls" in tool_name.lower()
            if is_emppersdtls:
                # Rule A: attribute-specific query strongly boosts EmpPersDtls.
                if detected_attribute:
                    final_score += 0.4
                    reasons.append("boost:attribute_query_emppersdtls")

                # Rule B: specific employee + generic detail keywords.
                if employee_name and has_details_signal:
                    final_score += 0.3
                    reasons.append("boost:employee_name_details_emppersdtls")

                # Rule C: list queries allow dynamic ranking but slight boost.
                if any(kw in query_lower for kw in list_keywords):
                    final_score += 0.1
                    reasons.append("boost:list_query_emppersdtls")

                # Employee list queries should also prefer EmpPersDtls for personal fields.
                if personal_list_query:
                    final_score += 0.35
                    reasons.append("boost:personal_list_query_emppersdtls")

                # Rule D: conflicting domains should avoid EmpPersDtls.
                if conflicting_domain:
                    final_score -= 0.5
                    reasons.append("penalty:conflicting_domain")

            final_score = max(0.0, min(1.0, final_score))
            self.last_reasons[tool_name] = reasons
            
            re_ranked.append((
                tool_name,
                final_score,
                semantic_score,
                keyword_score,
                intent_score
            ))
        
        # Sort by final score descending
        re_ranked.sort(key=lambda x: x[1], reverse=True)
        
        return re_ranked

    def handle_ambiguity(self, query: str, top_candidates: List[str]) -> Optional[str]:
        """Resolve unclear selection by favoring EmpPersDtls only when query signals are strong."""
        if not top_candidates:
            return None

        detected_attribute = detect_requested_attribute(query)
        employee_name = extract_employee_name(query)
        query_lower = query.lower()
        conflicting_domain = any(keyword in query_lower for keyword in ["salary", "payroll", "bank", "leave"])

        has_employee_context = any(keyword in query_lower for keyword in ["employee", "employees", "emp"])
        is_list_query = any(kw in query_lower for kw in ["all", "list", "show all", "display", "retrieve all", "get all"])
        has_personal_list_signal = any(keyword in query_lower for keyword in ["name", "mobile", "phone", "contact", "email", "blood", "dob", "gender", "religion", "marital", "father", "husband"])

        if not conflicting_domain and (detected_attribute or employee_name or (is_list_query and has_employee_context and has_personal_list_signal)):
            if EMPPERSDTLS_TOOL in self.registry:
                return EMPPERSDTLS_TOOL
            for candidate in top_candidates:
                if "emppersdtls" in candidate.lower():
                    return candidate

        return top_candidates[0]

    def calculate_confidence(
        self,
        top_score: float,
        second_score: Optional[float] = None,
        semantic_component: float = 0.0,
        keyword_component: float = 0.0
    ) -> float:
        """Calculate confidence score for API selection."""
        confidence = min(1.0, top_score)
        
        if second_score is not None:
            score_margin = top_score - second_score
            margin_boost = min(0.2, score_margin * 0.5)
            confidence = min(1.0, confidence + margin_boost)
        
        if semantic_component > 0.7:
            confidence = min(1.0, confidence + 0.1)
        
        if keyword_component > 0.7:
            confidence = min(1.0, confidence + 0.05)
        
        return confidence

    def select_api(self, query: str) -> Dict:
        """Select best API for user query with confidence scoring."""
        normalized_query, _ = self.normalize_query(query)

        # Get semantic candidates
        semantic_candidates = self.vector_store.search_tools_with_scores(normalized_query or query, k=settings.SEMANTIC_SEARCH_K)
        semantic_scores_dict = {name: score for name, score in semantic_candidates}
        
        # Re-rank with hybrid scoring (applies list filter)
        re_ranked = self.re_rank_candidates(
            normalized_query or query,
            semantic_candidates,
            semantic_scores_dict,
            top_k=settings.HYBRID_TOP_K
        )
        
        if not re_ranked:
            logger.warning(f"No candidates found for query: {query}")
            return {
                "api": None,
                "confidence": 0.0,
                "status": "no_candidates",
                "top_candidates": [],
                "scores": {}
            }
        
        # Rule-based boost for employee queries
        query_lower = query.lower()
        if "employee" in query_lower and any(kw in query_lower for kw in ["list", "all", "names", "info", "show"]):
            boosted = []
            for name, score, sem_score, kw_score, int_score in re_ranked:
                api_lower = name.lower()
                # Boost general employee info APIs
                if any(marker in api_lower for marker in ["emppersdtls", "employment", "empfamily", "empbankaccount"]):
                    score = min(1.0, score + 0.15)
                boosted.append((name, score, sem_score, kw_score, int_score))
            re_ranked = sorted(boosted, key=lambda x: x[1], reverse=True)
        
        # Get top candidate
        (top_name, top_score, top_semantic, top_keyword, top_intent) = re_ranked[0]
        
        # Calculate confidence
        second_score = re_ranked[1][1] if len(re_ranked) > 1 else None
        confidence = self.calculate_confidence(top_score, second_score, top_semantic, top_keyword)
        
        # Determine status
        if top_score < LOW_CONFIDENCE_BLOCK:
            status = "unclear"
        elif confidence >= settings.CONFIDENCE_THRESHOLD_HIGH:
            status = "high_confidence"
        elif confidence >= settings.CONFIDENCE_THRESHOLD_LOW:
            status = "low_confidence"
        else:
            status = "unclear"
        
        # Prepare results
        top_3 = [
            {
                "name": name,
                "score": score,
                "semantic": sem_score,
                "keyword": kw_score,
                "intent": int_score
            }
            for name, score, sem_score, kw_score, int_score in re_ranked[:3]
        ]
        
        # Log details
        logger.info(f"API Selection for query: '{query}'")
        logger.info(f"  Normalized query: '{normalized_query}'")
        logger.info(f"  Top 3 candidates:")
        for candidate in top_3:
            logger.info(
                f"    - {candidate['name']}: score={candidate['score']:.3f} "
                f"(semantic={candidate['semantic']:.3f}, "
                f"keyword={candidate['keyword']:.3f}, "
                f"intent={candidate['intent']:.3f})"
            )
        logger.info(f"  Selected: {top_name}")
        logger.info(f"  Confidence: {confidence:.3f} (threshold: {settings.CONFIDENCE_THRESHOLD_LOW})")

        for name, score, sem_score, kw_score, int_score in re_ranked[3:]:
            logger.debug(
                "  Rejected: %s score=%.3f (semantic=%.3f, keyword=%.3f, intent=%.3f) reason=%s",
                name,
                score,
                sem_score,
                kw_score,
                int_score,
                ",".join(self.last_reasons.get(name, [])) or "lower_rank",
            )
        
        selected_tool = top_name if status != "unclear" else None
        
        return {
            "api": selected_tool,
            "confidence": confidence,
            "status": status,
            "top_candidates": [item["name"] for item in top_3],
            "scores": {
                "semantic": top_semantic,
                "keyword": top_keyword,
                "intent": top_intent,
                "final": top_score
            }
        }

    def get_tool_data(self, tool_name: str) -> Optional[Dict]:
        """Get tool data from registry."""
        return self.registry.get(tool_name)
