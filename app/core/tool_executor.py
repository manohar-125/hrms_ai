import requests
import logging
from app.config import settings

logger = logging.getLogger(__name__)
BASE_URL = settings.HRMS_API_BASE_URL
TOKEN = settings.HRMS_API_TOKEN


class ToolExecutor:

    def execute(self, tool_data: dict):

        endpoint = tool_data["endpoint"]
        method = tool_data["method"]

        url = f"{BASE_URL}{endpoint}"

        headers = {
            "Authorization": f"Bearer {TOKEN}"
        }

        # Log outgoing API request
        logger.info(f"[ToolExecutor] Calling: {url}")

        if method == "GET":
            response = requests.get(url, headers=headers)

        else:
            raise Exception("Unsupported HTTP method")

        if response.status_code != 200:
            raise Exception(f"HRMS API failed: {response.status_code}")

        return response.json()