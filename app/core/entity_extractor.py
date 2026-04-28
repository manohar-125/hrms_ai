import re


def _clean_extracted_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_employee_name(question: str) -> str | None:
    """
    Extract employee name from common phrasings.
    Examples:
    - personal details of aman kumar
    - show details for aman
    - employee aman kumar details
    """
    q = question.strip()

    patterns = [
        r"\b(?:of|for)\s+([a-zA-Z][a-zA-Z\s\.-]{1,60})$",
        r"\bemployee\s+([a-zA-Z][a-zA-Z\s\.-]{1,60})(?:\s+details|\s+info|\s+information)?\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, q, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = _clean_extracted_name(match.group(1))
        if len(candidate) >= 2:
            return candidate

    # Fallback: capture title-cased token sequences (e.g., "Aman Kumar").
    title_case = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b", q)
    if title_case:
        candidate = _clean_extracted_name(title_case[-1])
        if len(candidate) >= 2:
            return candidate

    return None


def extract_entities(question: str):

    entities = {}

    # Extract numeric IDs
    id_match = re.search(r'\b\d+\b', question)

    if id_match:
        entities["id"] = int(id_match.group())

    employee_name = extract_employee_name(question)
    if employee_name:
        entities["employee_name"] = employee_name

    return entities


def detect_requested_attribute(question: str) -> str | None:
    """Detect personal attribute requested in a user question."""
    query = (question or "").lower()
    attribute_aliases = {
        "email": ["email", "mail", "email id"],
        "mobile": ["mobile", "phone", "contact number"],
        "blood_group": ["blood group", "blood"],
        "dob": ["dob", "date of birth", "birth date"],
        "gender": ["gender", "sex"],
        "religion": ["religion", "religious"],
        "marital_status": ["marital status", "married", "single"],
        "father_name": ["father name", "father"],
        "mother_name": ["mother name", "mother"],
    }

    for attribute, aliases in attribute_aliases.items():
        if any(alias in query for alias in aliases):
            return attribute
    return None