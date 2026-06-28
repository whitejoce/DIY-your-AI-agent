import json

from .base import ToolSpec, truncate


REMEMBER_TOOL = {
    "type": "function",
    "name": "remember",
    "description": "Persist an important user preference, project fact, or durable note.",
    "parameters": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Memory text to store."},
            "scope": {
                "type": "string",
                "description": "Memory scope. Defaults to global.",
            },
            "metadata": {
                "type": "object",
                "description": "Optional JSON metadata for this memory.",
            },
        },
        "required": ["content"],
        "additionalProperties": False,
    },
}

MEMORY_SEARCH_TOOL = {
    "type": "function",
    "name": "memory_search",
    "description": "Search persistent memory with case-insensitive keyword matching.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keyword query."},
            "scope": {"type": "string", "description": "Optional memory scope."},
            "limit": {
                "type": "integer",
                "description": "Maximum number of memories to return. Defaults to 5.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}


class MemoryToolProvider:
    def __init__(self, memory_store):
        self.memory_store = memory_store

    def load_tools(self):
        return [
            ToolSpec(
                definition=REMEMBER_TOOL,
                handler=self.remember,
                source="memory",
                requires_approval=True,
            ),
            ToolSpec(
                definition=MEMORY_SEARCH_TOOL,
                handler=self.memory_search,
                source="memory",
            ),
        ]

    def remember(self, args):
        record = self.memory_store.add(
            {
                "content": args["content"],
                "scope": args.get("scope") or "global",
                "metadata": args.get("metadata") or {},
            }
        )
        return "OK: remembered {0}".format(record["content"])

    def memory_search(self, args):
        results = self.memory_store.search(
            args.get("query") or "",
            scope=args.get("scope"),
            limit=int(args.get("limit") or 5),
        )
        if not results:
            return "No memories found"
        return truncate(json.dumps(results, ensure_ascii=False, indent=2))
