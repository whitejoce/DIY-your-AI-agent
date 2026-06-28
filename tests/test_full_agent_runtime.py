import json

from full_agent.approval import ApprovalPolicy
from full_agent.config import AgentConfig
from full_agent.model import ModelResponse, ToolCall
from full_agent.runtime import AgentRuntime
from full_agent.skills import SkillLoader
from full_agent.tools import ToolRegistry, ToolSpec


class FakeModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.inputs = []
        self.tools = []

    def create_response(self, input_messages, tools):
        self.inputs.append(input_messages)
        self.tools.append(tools)
        return self.responses.pop(0)


def make_registry():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            definition={
                "type": "function",
                "name": "echo",
                "parameters": {"type": "object"},
            },
            handler=lambda args: "echo {0}".format(args["value"]),
            source="test",
        )
    )
    return registry


def test_runtime_executes_tool_call_and_records_final_answer(tmp_path):
    model = FakeModel(
        [
            ModelResponse(
                output_text="",
                tool_calls=[
                    ToolCall(
                        name="echo",
                        call_id="call_1",
                        arguments=json.dumps({"value": "hello"}),
                    )
                ],
            ),
            ModelResponse(output_text="done"),
        ]
    )
    runtime = AgentRuntime(
        config=AgentConfig(max_turns=3, memory_path=tmp_path / "memory.jsonl"),
        model_client=model,
        registry=make_registry(),
        approval_policy=ApprovalPolicy(),
        skill_loader=SkillLoader(tmp_path / "skills"),
    )

    assert runtime.run("say hello") == "done"
    assert runtime.conversation.messages[-1] == {"role": "assistant", "content": "done"}
    assert {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": "echo hello",
    } in runtime.conversation.messages


def test_runtime_returns_max_turns_message(tmp_path):
    model = FakeModel(
        [
            ModelResponse(
                output_text="",
                tool_calls=[ToolCall(name="echo", call_id="call_1", arguments="{}")],
            )
        ]
    )
    runtime = AgentRuntime(
        config=AgentConfig(max_turns=1, memory_path=tmp_path / "memory.jsonl"),
        model_client=model,
        registry=make_registry(),
        approval_policy=ApprovalPolicy(),
        skill_loader=SkillLoader(tmp_path / "skills"),
    )

    assert runtime.run("loop") == "Reached the maximum number of turns"


def test_runtime_injects_selected_skill_instructions(tmp_path):
    skill_dir = tmp_path / "skills" / "pytest-helper"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "name": "pytest-helper",
                "description": "Testing guidance",
                "triggers": ["pytest"],
                "instructions": "SKILL.md",
            }
        ),
        encoding="utf-8",
    )
    (skill_dir / "SKILL.md").write_text("Use pytest.", encoding="utf-8")
    model = FakeModel([ModelResponse(output_text="ok")])
    runtime = AgentRuntime(
        config=AgentConfig(max_turns=1, memory_path=tmp_path / "memory.jsonl"),
        model_client=model,
        registry=make_registry(),
        approval_policy=ApprovalPolicy(),
        skill_loader=SkillLoader(tmp_path / "skills"),
    )

    runtime.run("run pytest")

    assert "Use pytest." in model.inputs[0][0]["content"]
