import json

from full_agent import model as model_module
from full_agent.config import ModelConfig
from full_agent.model import (
    OpenAIChatCompletionsModel,
    OpenAIResponsesModel,
    create_model_client,
)


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def model_dump(self, exclude_none=True):
        return dict(self.__dict__)


def test_model_factory_selects_openai_responses(monkeypatch):
    monkeypatch.setattr(model_module, "OpenAI", lambda **kwargs: Obj())

    client = create_model_client(ModelConfig(api="responses", api_key="key"))

    assert isinstance(client, OpenAIResponsesModel)


def test_model_factory_selects_openai_chat_completions(monkeypatch):
    monkeypatch.setattr(model_module, "OpenAI", lambda **kwargs: Obj())

    client = create_model_client(
        ModelConfig(api="chat_completions", api_key="key")
    )

    assert isinstance(client, OpenAIChatCompletionsModel)


def test_chat_completions_adapter_converts_messages_tools_and_tool_calls(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return Obj(
                choices=[
                    Obj(
                        message=Obj(
                            content="",
                            tool_calls=[
                                Obj(
                                    id="call_2",
                                    function=Obj(
                                        name="echo",
                                        arguments=json.dumps({"value": "next"}),
                                    ),
                                )
                            ],
                        )
                    )
                ]
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = Obj(completions=FakeCompletions())

    monkeypatch.setattr(model_module, "OpenAI", FakeOpenAI)
    client = OpenAIChatCompletionsModel(
        ModelConfig(model="chat-model", api_key="key", max_tokens=77, temperature=0.1)
    )

    response = client.create_response(
        [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "hello"},
            {
                "type": "function_call",
                "name": "echo",
                "call_id": "call_1",
                "arguments": json.dumps({"value": "hello"}),
            },
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": "echo hello",
            },
        ],
        [
            {
                "type": "function",
                "name": "echo",
                "description": "Echo input",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                },
            }
        ],
    )

    assert captured["model"] == "chat-model"
    assert captured["max_tokens"] == 77
    assert captured["temperature"] == 0.1
    assert captured["messages"][2]["role"] == "assistant"
    assert captured["messages"][2]["tool_calls"][0]["id"] == "call_1"
    assert captured["messages"][3] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "echo hello",
    }
    assert captured["tools"][0]["function"]["name"] == "echo"
    assert response.tool_calls[0].name == "echo"
    assert response.tool_calls[0].call_id == "call_2"
    assert json.loads(response.tool_calls[0].arguments) == {"value": "next"}


def test_model_factory_rejects_unknown_provider():
    try:
        create_model_client(ModelConfig(provider="missing", api_key="key"))
    except ValueError as e:
        assert str(e) == "Unsupported model provider: missing"
    else:
        raise AssertionError("expected unsupported provider to fail")
