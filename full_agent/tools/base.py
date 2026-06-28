from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol


MAX_TOOL_OUTPUT = 4000


def truncate(text, limit=None):
    text = str(text)
    if limit is None:
        limit = MAX_TOOL_OUTPUT
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... truncated to {0} chars".format(limit)


@dataclass(frozen=True)
class ToolSpec:
    definition: Dict[str, Any]
    handler: Callable[[Any], str]
    source: str = "builtin"
    requires_approval: bool = False

    @property
    def name(self):
        return self.definition["name"]


class ToolProvider(Protocol):
    def load_tools(self):
        ...


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, tool_spec):
        name = tool_spec.name
        if name in self._tools:
            raise ValueError("Tool already registered: {0}".format(name))
        self._tools[name] = tool_spec

    def load_provider(self, provider):
        for tool_spec in provider.load_tools():
            self.register(tool_spec)

    def get(self, name):
        return self._tools.get(name)

    def definitions(self):
        return [tool.definition for tool in self._tools.values()]

    def list(self):
        return list(self._tools.values())

    def names(self):
        return list(self._tools.keys())


class ToolExecutor:
    def __init__(self, registry, approval_policy):
        self.registry = registry
        self.approval_policy = approval_policy

    def execute(self, name, args):
        tool_spec = self.registry.get(name)
        if tool_spec is None:
            return "ERROR: unknown tool {0}".format(name)
        if not self.approval_policy.request_approval(tool_spec, args):
            return "ERROR: user rejected tool call {0}".format(name)
        try:
            return truncate(tool_spec.handler(args))
        except Exception as e:
            return "ERROR: tool {0} failed: {1}".format(name, e)
