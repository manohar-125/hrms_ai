import requests
import json
import re

SWAGGER_URL = "https://hrmsapilive.leanxpert.in/swagger/v1/swagger.json"
OUTPUT_FILE = "app/tools/api_registry.json"


def detect_domain(endpoint):

    endpoint = endpoint.lower()

    if "employee" in endpoint or "emp" in endpoint:
        return "employee"
    if "leave" in endpoint:
        return "leave"
    if "salary" in endpoint:
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


def extract_parameters(endpoint):

    params = re.findall(r"{(.*?)}", endpoint)

    param_dict = {}

    for p in params:

        if "empregid" in p.lower():
            param_dict[p] = "employee registration id"
        elif "id" in p.lower():
            param_dict[p] = "resource id"
        else:
            param_dict[p] = p

    return param_dict


def generate_description(endpoint):

    parts = endpoint.replace("/api/", "").split("/")

    resource = parts[0]

    if "{" in endpoint:
        return f"Fetch {resource} details using parameters"

    return f"Fetch all {resource} records"


def build_registry():

    print("Fetching Swagger spec...")

    response = requests.get(SWAGGER_URL)

    spec = response.json()

    registry = {}

    paths = spec.get("paths", {})

    for path, methods in paths.items():

        if "get" not in methods:
            continue

        tool_name = path.replace("/api/", "").replace("/", "_").replace("{", "").replace("}", "").lower()

        registry[f"get_{tool_name}"] = {
            "domain": detect_domain(path),
            "endpoint": path,
            "method": "GET",
            "description": generate_description(path),
            "parameters": extract_parameters(path)
        }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(registry, f, indent=2)

    print(f"Registry generated with {len(registry)} APIs")


if __name__ == "__main__":
    build_registry()