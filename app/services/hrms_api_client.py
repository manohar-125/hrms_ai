import requests
import logging
from app.config import settings

BASE_URL = settings.HRMS_API_BASE_URL
TOKEN = settings.HRMS_API_TOKEN
logger = logging.getLogger(__name__)


def get(endpoint: str, params: dict | None = None):
    """
    Generic GET request to HRMS API
    """

    url = f"{BASE_URL}{endpoint}"

    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        return {
            "success": True,
            "data": response.json()
        }

    except requests.exceptions.HTTPError as http_err:
        return {
            "success": False,
            "error": f"HTTP error occurred: {str(http_err)}"
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection error: Unable to reach HRMS API"
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout: HRMS API took too long to respond"
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Unexpected request error: {str(e)}"
        }


def fetch_policy_from_api():
    """
    Fetch policy documents from HRMS API.
    Primary endpoint: /api/Policies
    Fallback endpoint: /LeavePolicy
    """

    logger.info("Fetching policies from endpoint: /api/Policies")
    result = get("/api/Policies")

    if not result["success"]:
        logger.warning("Primary policy endpoint failed, trying fallback /LeavePolicy")
        result = get("/LeavePolicy")

    if not result["success"]:
        logger.warning("Failed to fetch policies from both endpoints")
        return None

    data = result["data"]
    if isinstance(data, list):
        logger.info("Policies API returned %d records", len(data))
    else:
        logger.info("Policies API returned non-list payload type: %s", type(data).__name__)

    return data


def download_binary(url: str):
    """
    Download a binary file (used for policy PDFs).
    """

    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }

    try:
        logger.info("Downloading policy PDF from URL: %s", url)
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        logger.info("Policy PDF downloaded successfully (bytes=%d)", len(response.content))
        return response.content
    except requests.exceptions.RequestException as exc:
        logger.warning("Failed downloading binary from %s: %s", url, str(exc))
        return None