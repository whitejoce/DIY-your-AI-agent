from mini_agent.tools import BUILTIN_TOOLS

from .base import ToolSpec


class BuiltinToolProvider:
    def load_tools(self):
        tools = []
        for tool in BUILTIN_TOOLS:
            tools.append(
                ToolSpec(
                    definition=tool.definition,
                    handler=tool.handler,
                    source="builtin",
                    requires_approval=tool.requires_approval,
                )
            )
        return tools
