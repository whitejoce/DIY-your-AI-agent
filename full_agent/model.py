from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

from dotenv import load_dotenv
from openai import OpenAI


@dataclass
class ToolCall:
    name: str
    call_id: str
    arguments: str
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_response_message(self):
        if self.raw:
            return dict(self.raw)
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


class ModelClient(Protocol):
    def create_response(self, input_messages, tools):
        ...


class OpenAIResponsesModel:
    def __init__(self, config):
        load_dotenv()
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
        tool_calls = []
        for item in response.output:
            if getattr(item, "type", None) != "function_call":
                continue
            raw = item.model_dump(exclude_none=True) if hasattr(item, "model_dump") else {}
            tool_calls.append(
                ToolCall(
                    name=item.name,
                    call_id=item.call_id,
                    arguments=item.arguments,
                    raw=raw,
                )
            )
        return ModelResponse(output_text=response.output_text, tool_calls=tool_calls)
