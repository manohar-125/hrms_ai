class ToolValidator:

    def __init__(self, registry: dict):
        self.registry = registry

    def validate(self, tool_name: str):

        if not tool_name:
            return False, "No tool selected."

        if tool_name not in self.registry:
            return False, f"Invalid tool: {tool_name}"

        tool = self.registry[tool_name]

        if "endpoint" not in tool:
            return False, "Tool endpoint missing."

        if "method" not in tool:
            return False, "Tool HTTP method missing."

        return True, tool