import json

from .approval import ApprovalPolicy
from .config import AgentConfig
from .context import ContextManager, ConversationMemory
from .memory import MemoryStore
from .model import ModelResponse, OpenAIResponsesModel
from .skills import SkillLoader
from .tools import BuiltinToolProvider, MemoryToolProvider, ToolExecutor, ToolRegistry


SYSTEM_PROMPT = """You are a helpful terminal assistant using the ReAct pattern.
When a tool is needed, call it with JSON arguments that match the tool schema.
Treat tool results as observations: reason over them internally, then give the user a clear natural-language answer.
Use persistent memory only for durable preferences or project facts.
Do not expose raw tool-call JSON or raw observation JSON unless the user explicitly asks for it.
Keep the final response concise and directly useful.
""".strip()


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
        self.model_client = model_client or OpenAIResponsesModel(self.config)
        self.system_prompt = SYSTEM_PROMPT
        self.tool_observer = tool_observer

    def run(self, task):
        self.conversation.add_user(task)
        selected_skills = self.skill_loader.select(task)
        skill_instructions = self.skill_loader.load_instructions(selected_skills)

        for _ in range(self.config.max_turns):
            response = self.model_client.create_response(
                self.context_manager.build_input(
                    self.system_prompt,
                    self.conversation.all(),
                    skill_instructions=skill_instructions,
                ),
                self.registry.definitions(),
            )
            if not response.tool_calls:
                self.conversation.add_assistant(response.output_text or "")
                return response.output_text

            self._record_tool_calls(response)

        return "Reached the maximum number of turns"

    def _record_tool_calls(self, response):
        for tool_call in response.tool_calls:
            self.conversation.add_tool_call(tool_call)
            output = self._execute_tool_call(tool_call)
            self.conversation.add_tool_output(tool_call.call_id, output)

    def _execute_tool_call(self, tool_call):
        try:
            args = json.loads(tool_call.arguments)
        except (json.JSONDecodeError, TypeError) as e:
            message = getattr(e, "msg", str(e))
            return "ERROR: invalid JSON arguments: {0}".format(message)
        if self.config.show_tool_calls and self.tool_observer is not None:
            self.tool_observer(tool_call.name, args)
        return self.executor.execute(tool_call.name, args)
