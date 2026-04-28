import json
import re
from pathlib import Path

import requests

SWAGGER_URL = "https://hrmsapi.leanxpert.in/swagger/v1/swagger.json"
OUTPUT_FILE = Path("app/tools/api_registry.json")


def detect_domain(endpoint: str) -> str:
    endpoint = endpoint.lower()

    if "employee" in endpoint or "emp" in endpoint:
        return "employee"
    if "leave" in endpoint:
        return "leave"
    if "salary" in endpoint or "payroll" in endpoint:
        return "payroll"
    if "project" in endpoint:
        return "project"
    if "task" in endpoint:
        return "task"
    if "asset" in endpoint:
        return "asset"
    if "attendance" in endpoint:
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
    parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    parts = re.sub(r"[^a-zA-Z0-9]+", " ", parts)
    return [w.lower() for w in parts.split() if w.strip()]


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


def build_keywords(tool_key: str, endpoint: str, parameters: dict):
    segments = endpoint.replace("/api/", "").split("/")
    words = []

    for segment in segments:
        if not segment or segment.startswith("{"):
            continue
        words.extend(split_words(segment))

    words.extend(split_words(tool_key))
    words.extend(split_words(" ".join(parameters.keys())))

    deduped = []
    seen = set()
    for w in words:
        if w not in seen:
            seen.add(w)
            deduped.append(w)

    return deduped[:8] if deduped else [resource_from_path(endpoint).lower()]


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
    normalized_name = tool_key
    normalized_intent = domain_to_intent(domain)

    return {
        "domain": domain,
        "endpoint": path,
        "method": "GET",
        "description": generate_description(path, method_spec),
        "parameters": parameters,
        "keywords": build_keywords(tool_key, path, parameters),
        "normalized_name": normalized_name,
        "normalized_intent": normalized_intent,
    }


def merge_existing(existing: dict, generated: dict) -> dict:
    merged = generated.copy()

    # Keep enriched metadata from existing entries when available.
    for optional_key in ("description", "keywords", "normalized_name", "normalized_intent"):
        existing_value = existing.get(optional_key)
        if existing_value not in (None, "", []):
            merged[optional_key] = existing_value

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