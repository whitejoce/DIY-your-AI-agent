import json

import mini_agent.agent as agent_module
from mini_agent import tools as tools_module


class FakeOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeToolCall:
    type = "function_call"

    def __init__(self, name="echo", call_id="call_123", arguments=None):
        self.name = name
        self.call_id = call_id
        self.arguments = arguments or json.dumps({"value": "hello"})

    def model_dump(self, exclude_none=True):
        return {
            "type": self.type,
            "name": self.name,
            "call_id": self.call_id,
            "arguments": self.arguments,
        }


def make_agent(monkeypatch):
    monkeypatch.setattr(agent_module, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(agent_module, "load_dotenv", lambda: None)
    return agent_module.Agent()


def test_register_tool_binds_definition_and_handler(monkeypatch):
    agent = make_agent(monkeypatch)

    def handler(args):
        return "ok"

    definition = {"type": "function", "name": "custom_tool"}
    agent.register_tool(definition, handler, requires_approval=True)

    assert agent.tools == [definition]
    assert agent.tool_handlers == {"custom_tool": handler}
    assert agent.requires_approval("custom_tool") is True


def test_register_tool_accepts_tool_spec(monkeypatch):
    agent = make_agent(monkeypatch)

    def handler(args):
        return "ok"

    definition = {"type": "function", "name": "custom_tool"}
    spec = tools_module.ToolSpec(definition, handler, requires_approval=True)

    agent.register_tool(spec)

    assert agent.tools == [definition]
    assert agent.tool_handlers == {"custom_tool": handler}
    assert agent.requires_approval("custom_tool") is True


def test_register_tool_keeps_legacy_default_without_approval(monkeypatch):
    agent = make_agent(monkeypatch)

    def handler(args):
        return "ok"

    agent.register_tool({"type": "function", "name": "edit_file"}, handler)

    assert agent.requires_approval("edit_file") is False


def test_register_tool_rejects_duplicate_names(monkeypatch):
    agent = make_agent(monkeypatch)

    def handler(args):
        return "ok"

    agent.register_tool({"type": "function", "name": "custom_tool"}, handler)

    try:
        agent.register_tool({"type": "function", "name": "custom_tool"}, handler)
    except ValueError as e:
        assert str(e) == "Tool already registered: custom_tool"
    else:
        raise AssertionError("expected duplicate registration to fail")


def test_run_tool_returns_error_for_unknown_tool(monkeypatch):
    agent = make_agent(monkeypatch)

    output = agent.run_tool("missing_tool", {})

    assert output == "ERROR: unknown tool missing_tool"


def test_dangerous_tools_require_approval_by_default(monkeypatch):
    agent = make_agent(monkeypatch)
    for tool in tools_module.BUILTIN_TOOLS:
        agent.register_tool(tool)

    assert agent.requires_approval("edit_file") is True
    assert agent.requires_approval("exec_command") is True
    assert agent.requires_approval("read_file") is False


def test_dangerous_tool_is_rejected_without_console(monkeypatch):
    agent = make_agent(monkeypatch)
    called = False

    def handler(args):
        nonlocal called
        called = True
        return "ran"

    agent.register_tool(
        {"type": "function", "name": "edit_file"},
        handler,
        requires_approval=True,
    )

    output = agent.run_tool(
        "edit_file",
        {"path": "x", "start_line": 1, "end_line": 1, "replacement": "y"},
    )

    assert output == "ERROR: user rejected tool call edit_file"
    assert called is False


def test_bypass_approval_runs_dangerous_tool(monkeypatch):
    agent = make_agent(monkeypatch)
    agent.bypass_approval = True

    def handler(args):
        return f"wrote {args['path']}"

    agent.register_tool(
        {"type": "function", "name": "edit_file"},
        handler,
        requires_approval=True,
    )

    output = agent.run_tool(
        "edit_file",
        {"path": "x", "start_line": 1, "end_line": 1, "replacement": "y"},
    )

    assert output == "wrote x"


def test_run_tool_calls_parses_arguments_and_returns_function_output(monkeypatch):
    agent = make_agent(monkeypatch)
    received_args = []

    def handler(args):
        received_args.append(args)
        return f"echo {args['value']}"

    agent.register_tool({"type": "function", "name": "echo"}, handler)

    results = agent.run_tool_calls([FakeToolCall()])

    assert received_args == [{"value": "hello"}]
    assert results == [
        {
            "type": "function_call",
            "name": "echo",
            "call_id": "call_123",
            "arguments": json.dumps({"value": "hello"}),
        },
        {
            "type": "function_call_output",
            "call_id": "call_123",
            "output": "echo hello",
        },
    ]


def test_run_tool_calls_returns_error_for_malformed_json(monkeypatch):
    agent = make_agent(monkeypatch)
    called = False

    def handler(args):
        nonlocal called
        called = True
        return "ok"

    agent.register_tool({"type": "function", "name": "echo"}, handler)

    results = agent.run_tool_calls([FakeToolCall(arguments="{bad json")])

    assert called is False
    assert results[1]["type"] == "function_call_output"
    assert results[1]["call_id"] == "call_123"
    assert results[1]["output"] == "ERROR: invalid JSON arguments: Expecting property name enclosed in double quotes"


def test_run_tool_passes_arguments_to_handler(monkeypatch):
    agent = make_agent(monkeypatch)
    received_args = []

    def handler(args):
        received_args.append(args)
        return "ok"

    agent.register_tool({"type": "function", "name": "echo"}, handler)

    assert agent.run_tool("echo", ["not", "an", "object"]) == "ok"
    assert received_args == [["not", "an", "object"]]


def test_run_tool_returns_error_when_handler_raises(monkeypatch):
    agent = make_agent(monkeypatch)

    def handler(args):
        raise RuntimeError("boom")

    agent.register_tool({"type": "function", "name": "explode"}, handler)

    assert agent.run_tool("explode", {}) == "ERROR: tool explode failed: boom"
