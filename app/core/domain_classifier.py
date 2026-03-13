from app.llm.llama_client import generate_response


DOMAIN_PROMPT = """
You are a domain classifier for an HRMS AI assistant.

Classify the user's question into ONE of the following domains:

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

Return ONLY the domain word.

Examples:

Question: Show employee details
Domain: employee

Question: Show departments
Domain: department

Question: Show leave balance
Domain: leave

Question: What is leave policy
Domain: policy

Now classify this question:

Question:
{question}

Domain:
"""


def classify_domain(question: str):

    prompt = DOMAIN_PROMPT.format(question=question)

    response = generate_response(prompt)

    return response.strip().lower()