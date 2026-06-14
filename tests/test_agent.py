import json

import mini_agent.agent as agent_module


class FakeOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeToolCall:
    type = "function_call"
    name = "echo"
    call_id = "call_123"
    arguments = json.dumps({"value": "hello"})

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
    agent.register_tool(definition, handler)

    assert agent.tools == [definition]
    assert agent.tool_handlers == {"custom_tool": handler}


def test_run_tool_returns_error_for_unknown_tool(monkeypatch):
    agent = make_agent(monkeypatch)

    output = agent.run_tool("missing_tool", {})

    assert output == "ERROR: unknown tool missing_tool"


def test_dangerous_tools_require_approval_by_default(monkeypatch):
    agent = make_agent(monkeypatch)

    assert agent.requires_approval("write_file") is True
    assert agent.requires_approval("exec_command") is True
    assert agent.requires_approval("read_file") is False


def test_dangerous_tool_is_rejected_without_console(monkeypatch):
    agent = make_agent(monkeypatch)
    called = False

    def handler(args):
        nonlocal called
        called = True
        return "ran"

    agent.register_tool({"type": "function", "name": "write_file"}, handler)

    output = agent.run_tool("write_file", {"path": "x", "content": "y"})

    assert output == "ERROR: user rejected tool call write_file"
    assert called is False


def test_bypass_approval_runs_dangerous_tool(monkeypatch):
    agent = make_agent(monkeypatch)
    agent.bypass_approval = True

    def handler(args):
        return f"wrote {args['path']}"

    agent.register_tool({"type": "function", "name": "write_file"}, handler)

    output = agent.run_tool("write_file", {"path": "x", "content": "y"})

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
