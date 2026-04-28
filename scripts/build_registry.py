import json
import re
from pathlib import Path

import requests

SWAGGER_URL = "https://hrmsapilive.leanxpert.in/swagger/v1/swagger.json"
OUTPUT_FILE = Path("app/tools/api_registry.json")


def detect_domain(endpoint: str) -> str:
    """Detect domain from endpoint with improved accuracy."""
    endpoint = endpoint.lower()

    # Employee/HR-related APIs
    if "emppersdtls" in endpoint or "personal" in endpoint:
        return "employee"
    if "employment" in endpoint:
        return "employee"
    if "address" in endpoint and "employee" not in endpoint:
        return "employee"  # Addresses are employee data
    if "empfamily" in endpoint:
        return "employee"
    if "empidentity" in endpoint:
        return "employee"
    if "employee" in endpoint or "emp" in endpoint:
        return "employee"
    
    # Payroll/Compensation
    if "empbank" in endpoint or "bank" in endpoint:
        return "payroll"  # Bank details are payroll-related
    if "salary" in endpoint or "payroll" in endpoint:
        return "payroll"
    if "earning" in endpoint or "deduction" in endpoint:
        return "payroll"
    if "managesalary" in endpoint or "managepay" in endpoint:
        return "payroll"
    
    # Other domains
    if "leave" in endpoint:
        return "leave"
    if "project" in endpoint:
        return "project"
    if "task" in endpoint or "timesheet" in endpoint or "worklog" in endpoint:
        return "task"
    if "asset" in endpoint:
        return "asset"
    if "attendance" in endpoint or "checkin" in endpoint or "checkout" in endpoint:
        return "attendance"
    if "client" in endpoint:
        return "client"

    return "hr"


def domain_to_intent(domain: str) -> str:
    mapping = {
        "employee": "employee_profile",
        "leave": "leave_management",
        "payroll": "payroll_management",
        "project": "project_management",
        "task": "task_management",
        "attendance": "attendance_tracking",
        "client": "client_management",
        "asset": "asset_tracking",
    }
    return mapping.get(domain, "organization_structure")


def split_words(value: str):
    # Split camel-case and separators into simple lowercase words.
    # Handle special case: don't split common abbreviations like "emp", "hr", "qa"
    parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    parts = re.sub(r"[^a-zA-Z0-9]+", " ", parts)
    words = [w.lower() for w in parts.split() if w.strip()]
    
    # Filter out single letters unless they're part of a known abbreviation
    filtered = []
    known_abbrs = {"emp", "hr", "qa", "qa", "id"}
    for w in words:
        if len(w) > 1 or w in known_abbrs:
            filtered.append(w)
    
    return filtered


def extract_parameters(endpoint: str) -> dict:
    params = re.findall(r"{(.*?)}", endpoint)
    param_dict = {}

    for p in params:
        p_lower = p.lower()
        if "empregid" in p_lower:
            param_dict[p] = "employee registration id"
        elif "designation" in p_lower:
            param_dict[p] = "Designation name"
        elif p_lower == "name":
            param_dict[p] = "Skill Name"
        elif "id" in p_lower:
            param_dict[p] = "resource id"
        else:
            param_dict[p] = p

    return param_dict


def resource_from_path(endpoint: str) -> str:
    clean = endpoint.replace("/api/", "").strip("/")
    first = clean.split("/")[0] if clean else "resource"
    return first


def generate_description(endpoint: str, method_spec: dict) -> str:
    for key in ("summary", "description"):
        value = str(method_spec.get(key, "")).strip()
        if value:
            return value

    resource = resource_from_path(endpoint)
    if "{" in endpoint:
        return f"Retrieve {resource} details by parameter"
    return f"Retrieve {resource} records"


def build_keywords(tool_key: str, endpoint: str, parameters: dict, description: str = ""):
    """Build enriched keyword list from multiple sources."""
    segments = endpoint.replace("/api/", "").split("/")
    words = []

    # Extract from endpoint path
    for segment in segments:
        if not segment or segment.startswith("{"):
            continue
        words.extend(split_words(segment))

    # Extract from tool key
    words.extend(split_words(tool_key))
    
    # Extract from parameters
    words.extend(split_words(" ".join(parameters.keys())))
    
    # Extract from description for better semantic matching
    if description:
        # Extract important nouns and verbs from description
        desc_words = split_words(description)
        # Add words that look like domain concepts (longer words, not common words)
        important_words = [w for w in desc_words if len(w) > 3 and w not in {
            "retrieve", "get", "list", "show", "display", "include", "including",
            "that", "this", "from", "with", "for", "and", "the", "are", "is", "a", "an"
        }]
        words.extend(important_words[:4])  # Add up to 4 important words from description

    # Semantic enrichment for common patterns
    endpoint_lower = endpoint.lower()
    text_lower = (tool_key + " " + endpoint + " " + description).lower()
    
    # Add semantic keywords based on patterns
    if "address" in endpoint_lower:
        words.extend(["location", "street", "postal", "contact"])
    if "salary" in endpoint_lower or "pay" in endpoint_lower:
        words.extend(["compensation", "earning", "income", "payroll"])
    if "personal" in endpoint_lower or "persdtls" in endpoint_lower:
        words.extend(["profile", "details", "info", "information", "contact"])
    if "phone" in endpoint_lower or "mobile" in endpoint_lower:
        words.extend(["contact", "number", "communication"])
    if "email" in endpoint_lower or "mail" in endpoint_lower:
        words.extend(["contact", "message", "communication"])
    if "leave" in endpoint_lower:
        words.extend(["vacation", "time", "off", "absence", "approval"])
    if "attendance" in endpoint_lower:
        words.extend(["check", "in", "out", "time", "tracking", "present"])
    if "project" in endpoint_lower:
        words.extend(["assignment", "work", "delivery", "client"])
    if "task" in endpoint_lower:
        words.extend(["work", "item", "assignment", "tracking"])
    if "asset" in endpoint_lower:
        words.extend(["equipment", "device", "resource", "tracking"])
    if "bank" in endpoint_lower:
        words.extend(["account", "financial", "payment", "transfer"])
    if "education" in endpoint_lower or "certificate" in endpoint_lower:
        words.extend(["qualification", "training", "skill", "learning"])
    if "family" in endpoint_lower:
        words.extend(["dependent", "relative", "relation", "member"])
    if "skill" in endpoint_lower:
        words.extend(["competency", "ability", "expertise", "training"])
    if "policy" in endpoint_lower:
        words.extend(["rule", "guideline", "regulation", "compliance"])
    if "employment" in endpoint_lower:
        words.extend(["employee", "staff", "work", "contract"])

    # Deduplicate while preserving order
    deduped = []
    seen = set()
    for w in words:
        if w not in seen and len(w) > 0:
            seen.add(w)
            deduped.append(w)

    # Return up to 10 keywords (increased from 8 for better coverage)
    return deduped[:10] if deduped else [resource_from_path(endpoint).lower()]


def build_tool_key(path: str) -> str:
    tool_name = (
        path.replace("/api/", "")
        .replace("/", "_")
        .replace("{", "")
        .replace("}", "")
        .strip("_")
        .lower()
    )
    return f"get_{tool_name}"


def build_default_entry(tool_key: str, path: str, method_spec: dict) -> dict:
    domain = detect_domain(path)
    parameters = extract_parameters(path)
    description = generate_description(path, method_spec)
    normalized_name = tool_key
    normalized_intent = domain_to_intent(domain)

    return {
        "domain": domain,
        "endpoint": path,
        "method": "GET",
        "description": description,
        "parameters": parameters,
        "keywords": build_keywords(tool_key, path, parameters, description),
        "normalized_name": normalized_name,
        "normalized_intent": normalized_intent,
    }


def merge_existing(existing: dict, generated: dict) -> dict:
    merged = generated.copy()

    # Keep enriched metadata from existing entries when available.
    # BUT: Always use newly generated keywords (they are now enriched)
    # and new domain assignments (they are now more accurate)
    for optional_key in ("description", "normalized_name", "normalized_intent"):
        existing_value = existing.get(optional_key)
        if existing_value not in (None, "", []):
            merged[optional_key] = existing_value
    
    # For keywords: Only preserve if existing has rich keywords (>3)
    # Otherwise use the newly generated ones
    existing_keywords = existing.get("keywords", [])
    if existing_keywords and len(existing_keywords) > 3:
        # Has rich existing keywords - preserve them
        merged["keywords"] = existing_keywords
    # else: use newly generated keywords (already in merged)

    return merged


def load_existing_registry() -> dict:
    if not OUTPUT_FILE.exists():
        return {}

    with open(OUTPUT_FILE, "r") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def build_registry():
    print("Fetching Swagger spec...")

    response = requests.get(SWAGGER_URL, timeout=30)
    response.raise_for_status()
    spec = response.json()

    existing_registry = load_existing_registry()
    new_registry = {}

    paths = spec.get("paths", {})
    for path, methods in paths.items():
        if not path.startswith("/api/"):
            continue
        if "get" not in methods:
            continue

        tool_key = build_tool_key(path)
        generated = build_default_entry(tool_key, path, methods.get("get", {}))
        existing = existing_registry.get(tool_key, {})

        new_registry[tool_key] = merge_existing(existing, generated)

    ordered_registry = dict(sorted(new_registry.items(), key=lambda x: x[0]))

    with open(OUTPUT_FILE, "w") as f:
        json.dump(ordered_registry, f, indent=2)

    print(f"Registry generated with {len(ordered_registry)} APIs")


if __name__ == "__main__":
    build_registry()