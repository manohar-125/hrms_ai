from app.llm.llama_client import generate_response


VALID_DOMAINS = {
    "employee", "department", "attendance", "leave", "payroll",
    "project", "task", "client", "policy", "general"
}


DOMAIN_PROMPT = """
You are an HRMS domain classifier.

Your task: Classify the user question into exactly ONE domain.

Available domains (choose only one):
- employee (employee records, profiles, information, personal details, contacts)
- department (department data, structures, organization)
- attendance (attendance records, check-in/out, time tracking)
- leave (leave requests, balances, policies, approvals)
- payroll (salary, compensation, payments, deductions, bank accounts)
- project (projects, assignments, tracking)
- task (tasks, work items, assignments, timesheets)
- client (client records, relationships)
- policy (HR policies, guidelines, rules)
- general (other, unrelated, miscellaneous)

Classification Rules:
1. Return ONLY the domain name in lowercase.
2. Do NOT include explanations.
3. If multiple domains match, choose the PRIMARY domain.
4. Be strict: pick only the best match.

PRIORITY RULES (apply in order):
- "salary", "payroll", "bank account", "earning", "deduction", "compensation" → payroll
- "leave", "vacation", "time off", "absence" → leave
- "attendance", "check-in", "check-out" → attendance
- "project" → project
- "task", "timesheet", "worklog" → task
- "mobile", "phone", "email", "address", "personal", "details", "profile" → employee
- "employee", "emp", "staff" → employee
- "department" → department
- "client" → client
- "policy" → policy

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

Question: Get mobile number of john
Domain: employee

Question: Show salary details
Domain: payroll

Question: Bank account details
Domain: payroll

Question: Father name of emp 123
Domain: employee

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