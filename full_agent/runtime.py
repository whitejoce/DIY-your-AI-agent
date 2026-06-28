import json
from dataclasses import dataclass, field
from typing import Optional

from .approval import ApprovalPolicy
from .config import AgentConfig
from .context import ContextManager, ConversationMemory
from .memory import MemoryStore
from .model import ModelResponse, create_model_client
from .skills import SkillLoader
from .tools import BuiltinToolProvider, MemoryToolProvider, ToolExecutor, ToolRegistry


SYSTEM_PROMPT = """You are a helpful terminal assistant using the ReAct pattern.
When a tool is needed, call it with JSON arguments that match the tool schema.
Treat tool results as observations: reason over them internally, then give the user a clear natural-language answer.
Use persistent memory only for durable preferences or project facts.
Do not expose raw tool-call JSON or raw observation JSON unless the user explicitly asks for it.
Keep the final response concise and directly useful.
""".strip()


@dataclass
class RunState:
    task: str
    turn: int = 0
    selected_skills: list = field(default_factory=list)
    skill_instructions: str = ""
    input_messages: list = field(default_factory=list)
    tools: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)
    last_response: Optional[ModelResponse] = None
    final_output: Optional[str] = None


class RuntimeHooks:
    def before_run(self, runtime, state):
        pass

    def before_model_call(self, runtime, state, input_messages, tools):
        pass

    def after_model_response(self, runtime, state, response):
        pass

    def before_tool_call(self, runtime, state, tool_call, args):
        pass

    def after_tool_call(self, runtime, state, tool_call, args, output):
        pass

    def on_turn_end(self, runtime, state):
        pass

    def after_run(self, runtime, state):
        pass


class SequentialToolScheduler:
    def select_tool_calls(self, runtime, state, response):
        return list(response.tool_calls)


class AgentRuntime:
    def __init__(
        self,
        config=None,
        model_client=None,
        registry=None,
        approval_policy=None,
        memory_store=None,
        skill_loader=None,
        context_manager=None,
        tool_observer=None,
        hooks=None,
        tool_scheduler=None,
    ):
        self.config = config or AgentConfig.from_env()
        self.memory_store = memory_store or MemoryStore(self.config.memory_path)
        self.skill_loader = skill_loader or SkillLoader(self.config.skills_dir)
        self.context_manager = context_manager or ContextManager(
            self.config.context_budget_chars
        )
        self.conversation = ConversationMemory()
        self.registry = registry or ToolRegistry()
        if registry is None:
            self.registry.load_provider(BuiltinToolProvider())
            self.registry.load_provider(MemoryToolProvider(self.memory_store))
        self.approval_policy = approval_policy or ApprovalPolicy()
        self.executor = ToolExecutor(self.registry, self.approval_policy)
        self.model_client = model_client or create_model_client(self.config.model_config)
        self.system_prompt = SYSTEM_PROMPT
        self.tool_observer = tool_observer
        self.hooks = hooks or RuntimeHooks()
        self.tool_scheduler = tool_scheduler or SequentialToolScheduler()

    def run(self, task):
        state = RunState(task=task)
        self.conversation.add_user(task)
        state.selected_skills = self.skill_loader.select(task)
        state.skill_instructions = self.skill_loader.load_instructions(
            state.selected_skills
        )
        self.hooks.before_run(self, state)

        for _ in range(self.config.max_turns):
            state.turn += 1
            input_messages = self.context_manager.build_input(
                self.system_prompt,
                self.conversation.all(),
                skill_instructions=state.skill_instructions,
            )
            tools = self.registry.definitions()
            state.input_messages = input_messages
            state.tools = tools

            override = self.hooks.before_model_call(
                self, state, input_messages, tools
            )
            if override is not None:
                input_messages, tools = override
                state.input_messages = input_messages
                state.tools = tools

            response = self.model_client.create_response(input_messages, tools)
            state.last_response = response
            override_response = self.hooks.after_model_response(
                self, state, response
            )
            if override_response is not None:
                response = override_response
                state.last_response = response

            if not response.tool_calls:
                self.conversation.add_assistant(response.output_text or "")
                state.final_output = response.output_text
                self.hooks.after_run(self, state)
                return response.output_text

            self._record_tool_calls(response, state)
            self.hooks.on_turn_end(self, state)

        state.final_output = "Reached the maximum number of turns"
        self.hooks.after_run(self, state)
        return state.final_output

    def _record_tool_calls(self, response, state=None):
        for tool_call in self.tool_scheduler.select_tool_calls(
            self, state, response
        ):
            self.conversation.add_tool_call(tool_call)
            output = self._execute_tool_call(tool_call, state)
            self.conversation.add_tool_output(tool_call.call_id, output)

    def _execute_tool_call(self, tool_call, state=None):
        try:
            args = json.loads(tool_call.arguments)
        except (json.JSONDecodeError, TypeError) as e:
            message = getattr(e, "msg", str(e))
            return "ERROR: invalid JSON arguments: {0}".format(message)
        override_args = self.hooks.before_tool_call(self, state, tool_call, args)
        if override_args is not None:
            args = override_args
        if self.config.show_tool_calls and self.tool_observer is not None:
            self.tool_observer(tool_call.name, args)
        output = self.executor.execute(tool_call.name, args)
        override_output = self.hooks.after_tool_call(
            self, state, tool_call, args, output
        )
        if override_output is not None:
            output = override_output
        if state is not None:
            state.tool_results.append(
                {"tool_call": tool_call, "arguments": args, "output": output}
            )
        return output
