import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.json import JSON
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

if __package__:
    from .tools import BUILTIN_TOOLS, ToolSpec
else:  # pragma: no cover - supports `python mini_agent/agent.py`
    from tools import BUILTIN_TOOLS, ToolSpec

# Prompt layer: behavior constraints
SYSTEM_PROMPT = """You are a helpful terminal assistant using the ReAct pattern.
When a tool is needed, call it with JSON arguments that match the tool schema.
Before editing an existing file, read it first so you can use the correct line numbers.
Use edit_file for file changes. It replaces only the requested 1-based line range and keeps the rest of the file.
Treat tool results as observations: reason over them internally, then give the user a clear natural-language answer.
Do not expose raw tool-call JSON or raw observation JSON unless the user explicitly asks for it.
Keep the final response concise and directly useful.
""".strip()


class Agent:
    # ReAct orchestration loop, combining Prompt, Memory, and Tool Harness layers
    # API: OpenAI Responses API
    def __init__(self, max_turns=10, console=None, show_tool_calls=True):
        load_dotenv()
        self.client = OpenAI(
            api_key=os.getenv("API_KEY") or "replace_with_your_api_key",
            base_url=os.getenv("BASE_URL") or None,
        )
        self.model = os.getenv("MODEL") or "gpt-5.4-mini"
        self.temperature = 0.2
        self.max_tokens = 2048
        self.max_turns = max_turns
        self.system_prompt = SYSTEM_PROMPT
        self.tools = []
        self.tool_handlers = {}
        self.messages = []  # Memory layer: short-term context
        self.console = console
        self.show_tool_calls = show_tool_calls
        self.approval_required_tools = set()
        self.bypass_approval = False

    # Tool Harness layer: register a tool schema and bind its handler
    def register_tool(self, definition, handler=None, requires_approval=False):
        if isinstance(definition, ToolSpec):
            requires_approval = definition.requires_approval
            handler = definition.handler
            definition = definition.definition
        elif handler is None and isinstance(definition, tuple):
            definition, handler, *rest = definition
            if rest:
                requires_approval = bool(rest[0])
        if handler is None:
            raise TypeError("handler is required when registering a raw tool definition")

        name = definition["name"]
        if name in self.tool_handlers:
            raise ValueError(f"Tool already registered: {name}")

        self.tools.append(definition)
        self.tool_handlers[name] = handler
        if requires_approval:
            self.approval_required_tools.add(name)

    def run(self, task):
        self.messages.append({"role": "user", "content": task})
        for _ in range(self.max_turns):
            resp = self.client.responses.create(
                model=self.model,
                max_output_tokens=self.max_tokens,  # Model config: limit per-turn output length
                temperature=self.temperature,  # Model config: keep sampling stable
                input=[
                    {"role": "system", "content": self.system_prompt},
                    *self.messages,
                ],
                tools=self.tools,
            )
            tool_calls = [item for item in resp.output if item.type == "function_call"]
            if not tool_calls:
                return resp.output_text  # Task completed

            self.messages.extend(self.run_tool_calls(tool_calls))
        return "Reached the maximum number of turns"  # Safety fallback

    def run_tool_calls(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            results.append(tool_call.model_dump(exclude_none=True))
            try:
                args = json.loads(tool_call.arguments)
            except (json.JSONDecodeError, TypeError) as e:
                message = getattr(e, "msg", str(e))
                output = f"ERROR: invalid JSON arguments: {message}"
                args = {"raw_arguments": tool_call.arguments}
            else:
                output = self.run_tool(tool_call.name, args)
            self.display_tool_call(tool_call.name, args)
            results.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": output,
                }
            )
        return results

    def display_tool_call(self, name, args):
        if not self.console or not self.show_tool_calls:
            return
        self.console.print(
            Panel(
                JSON.from_data(args),
                title=f"Tool call: {name}",
                border_style="yellow",
            )
        )

    # Tool Harness layer: execute a tool call through the bound handler
    def run_tool(self, name, args):
        handler = self.tool_handlers.get(name)
        if not handler:
            return f"ERROR: unknown tool {name}"
        if self.requires_approval(name) and not self.request_tool_approval(name, args):
            return f"ERROR: user rejected tool call {name}"
        try:
            return handler(args)
        except Exception as e:
            return f"ERROR: tool {name} failed: {e}"

    def requires_approval(self, name):
        return not self.bypass_approval and name in self.approval_required_tools

    def request_tool_approval(self, name, args):
        if not self.console:
            return False
        self.console.print(
            Panel(
                JSON.from_data(args),
                title=f"Approval required: {name}",
                border_style="red",
            )
        )
        answer = Prompt.ask("Approve tool call?", choices=["y", "n"], default="n")
        return answer.lower() == "y"


if __name__ == "__main__":
    console = Console()
    agent = Agent(console=console)

    # Register built-in tools
    for tool in BUILTIN_TOOLS:
        agent.register_tool(tool)

    # Initial info panel showing system prompt and available tools
    console.print(
        Panel(
            "System prompt: [dim]" + SYSTEM_PROMPT + "[/dim]\n"
            "Built-in tools: [dim]"
            + ", ".join([t["name"] for t in agent.tools])
            + "[/dim]\n"
            "Commands: [bold]/exit[/bold], [bold]/quit[/bold], [bold]/bypass[/bold]",
            title="Agent Ready",
            border_style="cyan",
        )
    )

    # Main loop: get user input, run agent, display response
    while True:
        task = Prompt.ask("[bold cyan]User input[/bold cyan]")
        command = task.strip().lower()
        if command in ["/exit", "/quit", "exit", "quit"]:
            console.print("[dim]Exited[/dim]")
            break
        if command == "/bypass":
            agent.bypass_approval = not agent.bypass_approval
            status = "ON" if agent.bypass_approval else "OFF"
            console.print(f"[yellow]Approval bypass: {status}[/yellow]")
            continue

        result = agent.run(task)
        console.print(
            Panel(
                Markdown(result or ""),
                title="Assistant reply",
                border_style="green",
            )
        )
