import json
import logging
import re

from app.cache.redis_cache import get_cache, normalize_query, set_cache, should_skip_cache
from app.config import settings
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
- employee (employee records, profiles, information, personal details, contacts)
- department (department data, structures, organization)
- attendance (attendance records, check-in/out, time tracking)
- leave (leave requests, balances, policies, approvals)
- payroll (salary, compensation, payments, deductions, bank accounts)
- project (projects, assignments, tracking)
- task (tasks, work items, assignments, timesheets)
- client (client records, relationships)
- policy (HR policies, guidelines, rules)
- general (other, unrelated, miscellaneous)

Classification Rules:
1. Return ONLY valid JSON with a single "domain" key.
2. Do NOT include explanations.
3. If multiple domains match, choose the PRIMARY domain.
4. Be strict: pick only the best match.

PRIORITY RULES (apply in order):
- "salary", "payroll", "bank account", "earning", "deduction", "compensation" -> payroll
- "leave", "vacation", "time off", "absence" -> leave
- "attendance", "check-in", "check-out" -> attendance
- "project" -> project
- "task", "timesheet", "worklog" -> task
- "mobile", "phone", "email", "address", "personal", "details", "profile" -> employee
- "employee", "emp", "staff" -> employee
- "department" -> department
- "client" -> client
- "policy" -> policy

Output format:
{{"domain": "employee"}}

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

Question: Get mobile number of john
Domain: employee

Question: Show salary details
Domain: payroll

Question: Bank account details
Domain: payroll

Question: Father name of emp 123
Domain: employee

Now classify this question:

Question:
{question}

Domain:
"""


def _truncate_for_log(value: str, limit: int = 800) -> str:
    if not value:
        return ""
    return value if len(value) <= limit else f"{value[:limit]}..."


def _try_parse_json(text: str) -> dict | None:
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _normalize_domain(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower()


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
    provider_name = (settings.LLM_PROVIDER or "unknown").strip().lower()
    logger.info("[LLM REQUEST] provider=%s task=domain", provider_name)
    response = llm.generate(prompt)
    logger.info("[LLM RESPONSE] raw=%s", _truncate_for_log(response))

    parsed_json = _try_parse_json(response)
    domain = _normalize_domain(parsed_json.get("domain") if parsed_json else None)

    if not domain:
        retry_prompt = f"{prompt}\nReturn ONLY valid JSON. Do not include any extra text."
        logger.info("[LLM REQUEST] provider=%s task=domain retry=1", provider_name)
        retry_response = llm.generate(retry_prompt)
        logger.info("[LLM RESPONSE] raw=%s", _truncate_for_log(retry_response))
        parsed_json = _try_parse_json(retry_response)
        domain = _normalize_domain(parsed_json.get("domain") if parsed_json else None)

    if not domain:
        domain = response.strip().lower()

    # clean possible LLM prefixes
    if "domain:" in domain:
        domain = domain.split("domain:")[-1].strip()

    # sometimes LLM returns extra text
    domain = domain.split()[0].strip(".,:;!?\"'()[]{}") if domain else ""

    logger.info("[LLM PARSED] result=%s", domain or "")

    if domain in VALID_DOMAINS:
        if not cache_skipped:
            set_cache(cache_key, {"domain": domain}, ttl=3600)
        return domain

    if not cache_skipped:
        set_cache(cache_key, {"domain": "general"}, ttl=3600)
    return "general"