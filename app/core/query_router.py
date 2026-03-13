from app.core.intent_classifier import classify_intent


def route(question: str):

    intent = classify_intent(question)

    if intent == "policy":
        return "policy"

    return "data"