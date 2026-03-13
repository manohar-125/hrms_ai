import requests
from app.config import settings

BASE_URL = settings.HRMS_API_BASE_URL
TOKEN = settings.HRMS_API_TOKEN


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
    Fetch leave policy from HRMS API
    Used when embedding does not exist in vector DB
    """

    result = get("/LeavePolicy")

    if not result["success"]:
        return None

    data = result["data"]

    # convert JSON policy to text for embedding
    if isinstance(data, list):
        text = "\n".join([str(item) for item in data])
    else:
        text = str(data)

    return text