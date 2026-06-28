from rich.console import Console
from rich.json import JSON
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from .approval import ApprovalPolicy
from .config import AgentConfig
from .runtime import AgentRuntime, SYSTEM_PROMPT


def main():
    console = Console()
    config = AgentConfig.from_env()

    def approve(name, args):
        console.print(
            Panel(
                JSON.from_data(args),
                title="Approval required: {0}".format(name),
                border_style="red",
            )
        )
        answer = Prompt.ask("Approve tool call?", choices=["y", "n"], default="n")
        return answer.lower() == "y"

    approval_policy = ApprovalPolicy(approver=approve)
    def show_tool_call(name, args):
        console.print(
            Panel(
                JSON.from_data(args),
                title="Tool call: {0}".format(name),
                border_style="yellow",
            )
        )

    runtime = AgentRuntime(
        config=config,
        approval_policy=approval_policy,
        tool_observer=show_tool_call,
    )

    console.print(
        Panel(
            "System prompt: [dim]{0}[/dim]\nCommands: [bold]/exit[/bold], [bold]/quit[/bold], [bold]/bypass[/bold], [bold]/tools[/bold], [bold]/skills[/bold], [bold]/memory[/bold]".format(
                SYSTEM_PROMPT
            ),
            title="Full Agent Ready",
            border_style="cyan",
        )
    )

    while True:
        task = Prompt.ask("[bold cyan]User input[/bold cyan]")
        command = task.strip().lower()

        if command in ["/exit", "/quit", "exit", "quit"]:
            console.print("[dim]Exited[/dim]")
            break
        if command == "/bypass":
            approval_policy.bypass = not approval_policy.bypass
            status = "ON" if approval_policy.bypass else "OFF"
            console.print("[yellow]Approval bypass: {0}[/yellow]".format(status))
            continue
        if command == "/tools":
            _print_tools(console, runtime)
            continue
        if command == "/skills":
            _print_skills(console, runtime)
            continue
        if command == "/memory":
            _print_memory(console, runtime)
            continue

        result = runtime.run(task)
        console.print(
            Panel(
                Markdown(result or ""),
                title="Assistant reply",
                border_style="green",
            )
        )


def _print_tools(console, runtime):
    rows = []
    for tool in runtime.registry.list():
        approval = "approval" if runtime.approval_policy.requires_approval(tool) else "auto"
        rows.append("{0} [{1}, {2}]".format(tool.name, tool.source, approval))
    console.print(Panel("\n".join(rows) or "No tools registered", title="Tools"))


def _print_skills(console, runtime):
    skills = runtime.skill_loader.discover()
    rows = [
        "{0}: {1} (triggers: {2})".format(
            skill.name,
            skill.description,
            ", ".join(skill.triggers) or "-",
        )
        for skill in skills
    ]
    console.print(Panel("\n".join(rows) or "No skills discovered", title="Skills"))


def _print_memory(console, runtime):
    records = runtime.memory_store.list()
    console.print(Panel(JSON.from_data(records), title="Memory"))
