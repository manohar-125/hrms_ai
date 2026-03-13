import requests
import json
from app.config import settings


OLLAMA_URL = settings.OLLAMA_URL
LLM_MODEL = settings.LLM_MODEL


def generate_response(prompt: str) -> str:
    """
    Sends a prompt to the Ollama LLM and returns the generated response.
    """

    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        return data.get("response", "").strip()

    except requests.exceptions.RequestException as e:
        return f"LLM service error: {str(e)}"

    except Exception as e:
        return f"Unexpected LLM error: {str(e)}"


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

    return generate_response(prompt)