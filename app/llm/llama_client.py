import requests
import json
from app.config import settings


OLLAMA_URL = settings.OLLAMA_URL
LLM_MODEL = settings.LLM_MODEL
OLLAMA_TIMEOUT = settings.OLLAMA_TIMEOUT


def _prepare_api_response(api_response):
    """Trim large API payloads so Ollama gets a compact prompt."""

    payload = api_response

    if isinstance(payload, list):
        max_items = settings.LLM_MAX_API_ITEMS
        if max_items is not None and len(payload) > max_items:
            payload = payload[:max_items] + [{"_truncated": True, "_more_items": len(api_response) - max_items}]

    elif isinstance(payload, dict):
        max_items = settings.LLM_MAX_API_ITEMS
        data = payload.get("data")
        if isinstance(data, list) and max_items is not None and len(data) > max_items:
            payload = {
                **payload,
                "data": data[:max_items],
                "_truncated": True,
                "_more_items": len(data) - max_items,
            }

    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    max_chars = settings.LLM_MAX_API_RESPONSE_CHARS
    if max_chars is not None and len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"

    return text


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
            timeout=OLLAMA_TIMEOUT
        )

        if response.status_code >= 400:
            try:
                error_detail = response.json().get("error", response.text)
            except ValueError:
                error_detail = response.text
            raise requests.exceptions.HTTPError(
                f"{response.status_code} Client Error for url: {response.url} - {error_detail}"
            )

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

    response_text = _prepare_api_response(api_response)

    prompt = f"""
You are an HRMS assistant.

User question:
{question}

HRMS API response (JSON):
{response_text}

Instructions:
- Convert the API response into a clear natural language answer.
- If it is a list, format it nicely.
- If data is empty, say no data found.
- Do not explain JSON.
- Only return the final answer.

Answer:
"""

    return generate_response(prompt)