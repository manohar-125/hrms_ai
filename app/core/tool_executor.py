import requests
from app.config import settings


BASE_URL = settings.HRMS_API_BASE_URL
TOKEN = settings.HRMS_API_TOKEN


class ToolExecutor:

    def execute(self, tool_data: dict):

        endpoint = tool_data["endpoint"]
        method = tool_data["method"]

        url = f"{BASE_URL}{endpoint}"

        print("[ToolExecutor] Calling:", url)

        headers = {
            "Authorization": f"Bearer {TOKEN}"
        }

        if method == "GET":
            response = requests.get(url, headers=headers)

        else:
            raise Exception("Unsupported HTTP method")

        if response.status_code != 200:
            raise Exception(f"HRMS API failed: {response.status_code}")

        return response.json()