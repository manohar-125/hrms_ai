import re


def extract_entities(question: str):

    entities = {}

    # Extract numeric IDs
    id_match = re.search(r'\b\d+\b', question)

    if id_match:
        entities["id"] = int(id_match.group())

    return entities