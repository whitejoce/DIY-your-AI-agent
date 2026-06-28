from full_agent.approval import ApprovalPolicy
from full_agent.tools import ToolExecutor, ToolRegistry, ToolSpec


def make_tool(name, handler=None, requires_approval=False):
    return ToolSpec(
        definition={"type": "function", "name": name, "parameters": {"type": "object"}},
        handler=handler or (lambda args: "ok"),
        source="test",
        requires_approval=requires_approval,
    )


def test_registry_rejects_duplicate_tool_names():
    registry = ToolRegistry()
    registry.register(make_tool("echo"))

    try:
        registry.register(make_tool("echo"))
    except ValueError as e:
        assert str(e) == "Tool already registered: echo"
    else:
        raise AssertionError("expected duplicate tool registration to fail")


def test_approval_policy_defaults_to_dangerous_tool_names():
    policy = ApprovalPolicy()

    assert policy.requires_approval(make_tool("edit_file")) is True
    assert policy.requires_approval(make_tool("exec_command")) is True
    assert policy.requires_approval(make_tool("remember")) is True
    assert policy.requires_approval(make_tool("read_file")) is False


def test_executor_returns_unknown_tool_error():
    executor = ToolExecutor(ToolRegistry(), ApprovalPolicy())

    assert executor.execute("missing", {}) == "ERROR: unknown tool missing"


def test_executor_rejects_without_approver():
    registry = ToolRegistry()
    registry.register(make_tool("remember", requires_approval=True))
    executor = ToolExecutor(registry, ApprovalPolicy())

    assert executor.execute("remember", {"content": "x"}) == "ERROR: user rejected tool call remember"


def test_executor_catches_handler_errors():
    registry = ToolRegistry()

    def explode(args):
        raise RuntimeError("boom")

    registry.register(make_tool("explode", handler=explode))
    executor = ToolExecutor(registry, ApprovalPolicy())

    assert executor.execute("explode", {}) == "ERROR: tool explode failed: boom"


def test_executor_truncates_long_output():
    registry = ToolRegistry()
    registry.register(make_tool("long", handler=lambda args: "abcdef"))
    executor = ToolExecutor(registry, ApprovalPolicy())

    from full_agent.tools import base

    original = base.MAX_TOOL_OUTPUT
    try:
        base.MAX_TOOL_OUTPUT = 3
        assert executor.execute("long", {}) == "abc\n... truncated to 3 chars"
    finally:
        base.MAX_TOOL_OUTPUT = original
