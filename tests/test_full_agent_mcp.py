from full_agent.mcp import StaticMCPToolProvider
from full_agent.tools import ToolRegistry, ToolSpec


def make_tool(name):
    return ToolSpec(
        definition={"type": "function", "name": name, "parameters": {"type": "object"}},
        handler=lambda args: "from mcp",
        source="mcp:test",
    )


def test_static_mcp_provider_registers_and_executes_tool():
    registry = ToolRegistry()
    registry.load_provider(StaticMCPToolProvider([make_tool("mcp_echo")]))

    tool = registry.get("mcp_echo")

    assert tool is not None
    assert tool.handler({}) == "from mcp"


def test_static_mcp_provider_duplicate_tool_names_fail():
    registry = ToolRegistry()
    provider = StaticMCPToolProvider([make_tool("same"), make_tool("same")])

    try:
        registry.load_provider(provider)
    except ValueError as e:
        assert str(e) == "Tool already registered: same"
    else:
        raise AssertionError("expected duplicate MCP tool to fail")
