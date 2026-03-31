from app.llm.llama_client import generate_response


VALID_DOMAINS = {
    "employee", "department", "attendance", "leave", "payroll",
    "project", "task", "client", "policy", "general"
}


DOMAIN_PROMPT = """
You are an HRMS domain classifier.

Your task: Classify the user question into exactly ONE domain.

Available domains (choose only one):
- employee (employee records, profiles, information)
- department (department data, structures, organization)
- attendance (attendance records, check-in/out, time tracking)
- leave (leave requests, balances, policies, approvals)
- payroll (salary, compensation, payments, deductions)
- project (projects, assignments, tracking)
- task (tasks, work items, assignments)
- client (client records, relationships)
- policy (HR policies, guidelines, rules)
- general (other, unrelated, miscellaneous)

Classification Rules:
1. Return ONLY the domain name in lowercase.
2. Do NOT include explanations.
3. If multiple domains match, choose the PRIMARY domain.
4. Be strict: pick only the best match.

Examples:

Question: Show all employees
Domain: employee

Question: What departments exist
Domain: department

Question: Check my attendance
Domain: attendance

Question: Show my leave balance
Domain: leave

Question: List all projects
Domain: project

Question: What is the leave policy
Domain: policy

Now classify this question:

Question:
{question}

Domain:
"""


def classify_domain(question: str):

    prompt = DOMAIN_PROMPT.format(question=question)

    response = generate_response(prompt)

    domain = response.strip().lower()

    # clean possible LLM prefixes
    if "domain:" in domain:
        domain = domain.split("domain:")[-1].strip()

    # sometimes LLM returns extra text
    domain = domain.split()[0].strip(".,:;!?\"'()[]{}") if domain else ""

    if domain in VALID_DOMAINS:
        return domain

    return "general"