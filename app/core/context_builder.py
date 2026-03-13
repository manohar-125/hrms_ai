# simple in-memory conversation storage

conversation_store = {}


def add_to_context(session_id: str, question: str, answer: str):
    """
    Stores conversation history
    """

    if session_id not in conversation_store:
        conversation_store[session_id] = []

    conversation_store[session_id].append({
        "question": question,
        "answer": answer
    })


def get_context(session_id: str):
    """
    Returns previous conversation messages
    """

    return conversation_store.get(session_id, [])


def build_context_prompt(session_id: str):

    history = get_context(session_id)

    if not history:
        return ""

    context_text = ""

    for item in history[-5:]:  # keep last 5 messages
        context_text += f"User: {item['question']}\n"
        context_text += f"Assistant: {item['answer']}\n"

    return context_text