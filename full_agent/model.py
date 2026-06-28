import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

from openai import OpenAI


@dataclass
class ToolCall:
    name: str
    call_id: str
    arguments: str
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_response_message(self):
        return {
            "type": "function_call",
            "name": self.name,
            "call_id": self.call_id,
            "arguments": self.arguments,
        }


@dataclass
class ModelResponse:
    output_text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw: Any = None


class ModelClient(Protocol):
    def create_response(self, input_messages, tools):
        ...


def create_model_client(config):
    model_config = getattr(config, "model_config", config)
    provider = model_config.provider
    api = model_config.api

    if provider in {"openai", "openai_compatible"}:
        if api == "responses":
            return OpenAIResponsesModel(model_config)
        if api == "chat_completions":
            return OpenAIChatCompletionsModel(model_config)
        raise ValueError("Unsupported OpenAI model API: {0}".format(api))

    if provider == "anthropic":
        if api != "anthropic_messages":
            raise ValueError("Unsupported Anthropic model API: {0}".format(api))
        return AnthropicMessagesModel(model_config)

    raise ValueError("Unsupported model provider: {0}".format(provider))


class OpenAIResponsesModel:
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key or "replace_with_your_api_key",
            base_url=config.base_url,
        )

    def create_response(self, input_messages, tools):
        response = self.client.responses.create(
            model=self.config.model,
            max_output_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            input=input_messages,
            tools=tools,
        )
        return ModelResponse(
            output_text=_responses_output_text(response),
            tool_calls=_responses_tool_calls(response),
            raw=response,
        )


class OpenAIChatCompletionsModel:
    def __init__(self, config):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key or "replace_with_your_api_key",
            base_url=config.base_url,
        )

    def create_response(self, input_messages, tools):
        kwargs = {
            "model": self.config.model,
            "messages": _to_chat_messages(input_messages),
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        chat_tools = _to_chat_tools(tools)
        if chat_tools:
            kwargs["tools"] = chat_tools

        response = self.client.chat.completions.create(**kwargs)
        message = _first_chat_message(response)
        return ModelResponse(
            output_text=_value(message, "content") or "",
            tool_calls=_chat_tool_calls(message),
            raw=response,
        )


class AnthropicMessagesModel:
    def __init__(self, config):
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise RuntimeError(
                "Anthropic provider requires the optional 'anthropic' package."
            ) from e

        self.config = config
        kwargs = {}
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self.client = Anthropic(**kwargs)

    def create_response(self, input_messages, tools):
        system, messages = _to_anthropic_messages(input_messages)
        kwargs = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": messages,
        }
        anthropic_tools = _to_anthropic_tools(tools)
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = self.client.messages.create(**kwargs)
        return ModelResponse(
            output_text=_anthropic_output_text(response),
            tool_calls=_anthropic_tool_calls(response),
            raw=response,
        )


def _responses_output_text(response):
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    parts = []
    for item in getattr(response, "output", []) or []:
        if _value(item, "type") != "message":
            continue
        for content in _value(item, "content", []) or []:
            content_type = _value(content, "type")
            if content_type in {"output_text", "text"}:
                text = _value(content, "text")
                if text:
                    parts.append(text)
    return "".join(parts)


def _responses_tool_calls(response):
    tool_calls = []
    for item in getattr(response, "output", []) or []:
        if _value(item, "type") != "function_call":
            continue
        tool_calls.append(
            ToolCall(
                name=_value(item, "name"),
                call_id=_value(item, "call_id"),
                arguments=_value(item, "arguments") or "{}",
                raw=_dump_raw(item),
            )
        )
    return tool_calls


def _first_chat_message(response):
    choices = _value(response, "choices", []) or []
    if not choices:
        return {}
    return _value(choices[0], "message", {}) or {}


def _chat_tool_calls(message):
    tool_calls = []
    for call in _value(message, "tool_calls", []) or []:
        function = _value(call, "function", {}) or {}
        tool_calls.append(
            ToolCall(
                name=_value(function, "name"),
                call_id=_value(call, "id"),
                arguments=_value(function, "arguments") or "{}",
                raw=_dump_raw(call),
            )
        )
    return tool_calls


def _to_chat_messages(input_messages):
    messages = []
    for message in input_messages:
        message_type = message.get("type")
        if message_type == "function_call":
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": message["call_id"],
                            "type": "function",
                            "function": {
                                "name": message["name"],
                                "arguments": message.get("arguments") or "{}",
                            },
                        }
                    ],
                }
            )
            continue
        if message_type == "function_call_output":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": message["call_id"],
                    "content": str(message.get("output", "")),
                }
            )
            continue
        messages.append(
            {
                "role": message["role"],
                "content": message.get("content", ""),
            }
        )
    return messages


def _to_chat_tools(tools):
    chat_tools = []
    for tool in tools:
        if tool.get("type") != "function":
            continue
        if "function" in tool:
            chat_tools.append(tool)
            continue
        function = {
            "name": tool["name"],
            "parameters": tool.get("parameters") or {"type": "object"},
        }
        if tool.get("description"):
            function["description"] = tool["description"]
        chat_tools.append({"type": "function", "function": function})
    return chat_tools


def _to_anthropic_messages(input_messages):
    system_parts = []
    messages = []
    for message in input_messages:
        if message.get("role") == "system":
            system_parts.append(message.get("content", ""))
            continue

        message_type = message.get("type")
        if message_type == "function_call":
            messages.append(
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": message["call_id"],
                            "name": message["name"],
                            "input": _json_object(message.get("arguments") or "{}"),
                        }
                    ],
                }
            )
            continue
        if message_type == "function_call_output":
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": message["call_id"],
                            "content": str(message.get("output", "")),
                        }
                    ],
                }
            )
            continue

        messages.append(
            {
                "role": message["role"],
                "content": message.get("content", ""),
            }
        )
    return "\n\n".join(part for part in system_parts if part), messages


def _to_anthropic_tools(tools):
    anthropic_tools = []
    for tool in tools:
        if "input_schema" in tool:
            anthropic_tools.append(tool)
            continue
        if tool.get("type") != "function":
            continue

        if "function" in tool:
            function = tool["function"]
            name = function["name"]
            description = function.get("description", "")
            input_schema = function.get("parameters") or {"type": "object"}
        else:
            name = tool["name"]
            description = tool.get("description", "")
            input_schema = tool.get("parameters") or {"type": "object"}

        anthropic_tools.append(
            {
                "name": name,
                "description": description,
                "input_schema": input_schema,
            }
        )
    return anthropic_tools


def _anthropic_output_text(response):
    parts = []
    for block in _value(response, "content", []) or []:
        if _value(block, "type") == "text":
            text = _value(block, "text")
            if text:
                parts.append(text)
    return "".join(parts)


def _anthropic_tool_calls(response):
    tool_calls = []
    for block in _value(response, "content", []) or []:
        if _value(block, "type") != "tool_use":
            continue
        tool_calls.append(
            ToolCall(
                name=_value(block, "name"),
                call_id=_value(block, "id"),
                arguments=json.dumps(_value(block, "input", {}) or {}, ensure_ascii=False),
                raw=_dump_raw(block),
            )
        )
    return tool_calls


def _json_object(value):
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {"arguments": value}
    if isinstance(parsed, dict):
        return parsed
    return {"arguments": parsed}


def _value(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _dump_raw(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_none=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {}
