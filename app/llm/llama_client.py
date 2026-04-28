import json

from app.llm.llm_factory import get_llm


def generate_response(prompt: str) -> str:
    llm = get_llm()
    return llm.generate(prompt)


def generate_answer(question: str, api_response: dict) -> str:
    """
    Converts raw HRMS API JSON response into a readable answer using LLM.
    """

    prompt = f"""
You are an HRMS assistant.

User question:
{question}

HRMS API response (JSON):
{json.dumps(api_response, indent=2)}

Instructions:
- Convert the API response into a clear natural language answer.
- If it is a list, format it nicely.
- If data is empty, say no data found.
- Do not explain JSON.
- Only return the final answer.

Answer:
"""

    llm = get_llm()
    return llm.generate(prompt)