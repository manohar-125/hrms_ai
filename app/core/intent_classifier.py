from app.llm.llama_client import generate_response


INTENT_PROMPT = """
You are an intent classifier for an HRMS AI assistant.

Classify the user's question into ONE of these intents:

employee
department
attendance
leave
payroll
project
task
client
policy
general

Return ONLY the intent word.

Examples:

Question: Show all departments
Intent: department

Question: List departments
Intent: department

Question: Show employee details
Intent: employee

Question: What is leave policy
Intent: policy

Now classify this:

Question:
{question}

Intent:
"""


def classify_intent(question: str):

    prompt = INTENT_PROMPT.format(question=question)

    response = generate_response(prompt)

    return response.strip().lower()