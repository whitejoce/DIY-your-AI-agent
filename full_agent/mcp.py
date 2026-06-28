from typing import Protocol


class MCPToolProvider(Protocol):
    def load_tools(self):
        ...


class StaticMCPToolProvider:
    def __init__(self, tools, source="mcp:static"):
        self.tools = list(tools)
        self.source = source

    def load_tools(self):
        return list(self.tools)
