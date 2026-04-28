import logging

from app.cache.redis_cache import get_cache, normalize_query, set_cache, should_skip_cache
from app.llm.llm_factory import get_llm


VALID_DOMAINS = {
    "employee", "department", "attendance", "leave", "payroll",
    "project", "task", "client", "policy", "general"
}


logger = logging.getLogger(__name__)


DOMAIN_PROMPT = """
You are an HRMS domain classifier.

Your task: Classify the user question into exactly ONE domain.

Available domains (choose only one):
- employee (employee records, profiles, information)
- department (department data, structures, organization)
- attendance (attendance records, check-in/out, time tracking)
- leave (leave requests, balances, policies, approvals)
- payroll (salary, compensation, payments, deductions)
- project (projects, assignments, tracking)
- task (tasks, work items, assignments)
- client (client records, relationships)
- policy (HR policies, guidelines, rules)
- general (other, unrelated, miscellaneous)

Classification Rules:
1. Return ONLY the domain name in lowercase.
2. Do NOT include explanations.
3. If multiple domains match, choose the PRIMARY domain.
4. Be strict: pick only the best match.

Examples:

Question: Show all employees
Domain: employee

Question: What departments exist
Domain: department

Question: Check my attendance
Domain: attendance

Question: Show my leave balance
Domain: leave

Question: List all projects
Domain: project

Question: What is the leave policy
Domain: policy

Now classify this question:

Question:
{question}

Domain:
"""


def classify_domain(question: str):
    normalized_query = normalize_query(question)
    cache_key = f"domain:{normalized_query}"
    cache_skipped = should_skip_cache(question)

    if not cache_skipped:
        cached = get_cache(cache_key)
        if isinstance(cached, dict):
            cached_domain = (cached.get("domain") or "").strip().lower()
            if cached_domain in VALID_DOMAINS:
                logger.info("[CACHE HIT] domain:%s", normalized_query)
                return cached_domain
        logger.info("[CACHE MISS] domain:%s", normalized_query)

    prompt = DOMAIN_PROMPT.format(question=question)

    llm = get_llm()
    response = llm.generate(prompt)

    domain = response.strip().lower()

    # clean possible LLM prefixes
    if "domain:" in domain:
        domain = domain.split("domain:")[-1].strip()

    # sometimes LLM returns extra text
    domain = domain.split()[0].strip(".,:;!?\"'()[]{}") if domain else ""

    if domain in VALID_DOMAINS:
        if not cache_skipped:
            set_cache(cache_key, {"domain": domain}, ttl=3600)
        return domain

    if not cache_skipped:
        set_cache(cache_key, {"domain": "general"}, ttl=3600)
    return "general"