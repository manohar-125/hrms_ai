from app.llm.llama_client import generate_response


INTENT_PROMPT = """
You are an intent classifier for an HRMS AI assistant.

Your task: Classify the user question into exactly ONE intent category.

Available intents (choose only one):
- employee (queries about employee records, information, profiles)
- department (queries about departments, organization structure)
- attendance (queries about attendance, time tracking, check-in)
- leave (queries about leaves, balances, policies)
- payroll (queries about salary, compensation, payroll processing)
- project (queries about projects, assignments, tracking)
- task (queries about tasks, work items)
- client (queries about clients, relationships)
- policy (queries about HR policies, guidelines, rules)
- general (other queries, unrelated to specific categories)

Classification Rules:
1. Return ONLY the intent name in lowercase.
2. Do NOT include explanations or reasoning.
3. If multiple intents match, choose the PRIMARY intent.
4. Be strict and precise in your classification.

Examples:

Question: Show all departments
Intent: department

Question: List employees in HR
Intent: employee

Question: What is the leave policy
Intent: policy

Question: Check my attendance record
Intent: attendance

Question: Show project details
Intent: project

Now classify this question:

Question:
{question}

Intent:
"""


def classify_intent(question: str):

    prompt = INTENT_PROMPT.format(question=question)

    response = generate_response(prompt)

    return response.strip().lower()