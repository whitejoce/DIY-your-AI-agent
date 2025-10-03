#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Whitejoce
# use GPT-5 Codex optimized

import re
import json
import subprocess
import os
import pathlib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List

from openai import OpenAI
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown

class Agent:
    """Agent centralizes the state (API, prompt) and operations (max retry count)."""
    # check the API_SLOTS and SYSTEM_PROMPT before using
    API_SLOTS = {
        "openai": {
            "url": "https://api.openai.com/v1",
            "api_key": "your_api_key",
            "model": "gpt-4o",
        },
        "longcat": {
            "url": "https://api.longcat.chat/openai/v1/",
            "api_key": "your_api_key",
            "model": "LongCat-Flash-Chat",
        },
    }
    setting_api = "openai"  # default api slot name

    SYSTEM_PROMPT = """
    You are a Linux terminal assistant agent. Please strictly follow these rules:
    1. When the user requests system operations, produce the corresponding terminal command. When replying directly, use Markdown formatting.
    2. Dangerous commands must be confirmed a second time before execution.
    3. Execute only one command at a time.
    4. If the user asks to switch to a specific directory, instruct them to use the /cd command to change directories.
    5. Always format the output as JSON with one of the following structures:
       {
           "action": "execute_command",
           "command": "ls -l",
           "explanation": "Use ls to list detailed information in the current directory"
       }
       or
       {
           "action": "direct_reply",
           "content": "Hello, how can I help you today?"
       }
    """.strip()

    def __init__(self, api_slot_name: str, max_turns: int = 20):
        self.console = Console()
        self.api_config = self._setup_api_config(api_slot_name)
        self.client = OpenAI(api_key=self.api_config["api_key"], base_url=self.api_config["url"])
        self.session = SessionContext(system_prompt=self.SYSTEM_PROMPT, max_turns=max_turns)

    def _setup_api_config(self, api_slot_name: str) -> dict:
        """Configure and validate the API by name."""

        config = self.API_SLOTS.get(api_slot_name)
        if not config:
            raise ValueError(f"API slot '{api_slot_name}' not found.")

        assert (
            config["url"] != "your_url" and config["api_key"] != "your_api_key"
        ), "Please provide a valid url and api_key"
        return config

    def check_result(self, user_input: str, command_output: str) -> str:
        """Verify whether the command output meets the user's expectation."""

        prompt = f"""
        You are a task validation assistant. Based on the information below, determine whether the command met the user's expectation.

        User request: {user_input}
        Command output: {command_output}

        Respond with:
        - If it met the expectation, output "[✅] Success"
        - If it did not, output "[❌] Failure: explain the reason"
        """.strip()
        response = self.client.chat.completions.create(
            model=self.api_config["model"],
            messages=[{"role": "system", "content": prompt}],
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""

def get_chat_response(agent: Agent) -> tuple[str, str]:
    """Fetch the chat response."""

    response = agent.client.chat.completions.create(
        model=agent.api_config["model"],
        messages=agent.session.as_payload(),  # type: ignore[arg-type]
        stream=True,
    )
    reply_chunk, reasoning_chunk = [], []
    has_reasoning = False
    with console.status("[bold green]Thinking...[/bold green]") as status:
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                reply_chunk.append(content)

            reasoning_content = getattr(chunk.choices[0].delta, "model_extra", {}).get("reasoning_content")
            if reasoning_content:
                has_reasoning = True
                reasoning_chunk.append(reasoning_content)
                status.stop()
                console.print(reasoning_content, end="")

    if has_reasoning:
        print()
    return "".join(reply_chunk), "".join(reasoning_chunk)

@dataclass
class SessionContext:
    """SessionContext keeps shell state, chat history, and a finite state machine."""

    class State(Enum):
        AWAITING_USER_INPUT = auto()
        AWAITING_MODEL_RESPONSE = auto()

    system_prompt: str
    max_turns: int = 20
    messages: List[Dict[str, str]] = field(default_factory=list)
    retry_threshold: int = 3
    state: "SessionContext.State" = field(init=False, default=State.AWAITING_USER_INPUT)
    retry_count: int = field(init=False, default=0)

    def __post_init__(self):
        self.messages.append({"role": "system", "content": self.system_prompt})

    # --- Chat history management ---
    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self._trim_history()

    def add_user(self, content: str):
        self.add_message("user", content)

    def add_assistant(self, content: str):
        self.add_message("assistant", content)

    def add_system(self, content: str):
        self.add_message("system", content)

    # Limit chat history length to max_turns * 2
    def _trim_history(self):
        if self.max_turns <= 0:
            return
        max_messages = self.max_turns * 2
        overflow = len(self.messages) - 1 - max_messages
        if overflow > 0:
            del self.messages[1 : 1 + overflow]

    def as_payload(self) -> List[Dict[str, str]]:
        return [msg.copy() for msg in self.messages]

    # --- Shell state management ---
    @property
    def cwd(self) -> pathlib.Path:
        return pathlib.Path.cwd()

    def change_directory(self, path: str) -> tuple[bool, str]:
        try:
            target_path = pathlib.Path(path).expanduser()
            os.chdir(target_path)
            return True, f"Switched to directory: {os.getcwd()}"
        except FileNotFoundError:
            return False, f"[red]Error: directory '{path}' does not exist.[/red]"
        except Exception as e:
            return False, f"[red]Error while changing directory: {e}[/red]"

    # --- State machine ---
    @property
    def awaiting_user_input(self) -> bool:
        return self.state == self.State.AWAITING_USER_INPUT

    def advance_state(self, new_state: "SessionContext.State"):
        self.state = new_state
        if new_state == self.State.AWAITING_USER_INPUT:
            self.reset_retry_count()

    def reset_retry_count(self):
        self.retry_count = 0

    def register_retry_failure(self):
        self.retry_count += 1

    def has_exceeded_retry_threshold(self) -> bool:
        return self.retry_count > self.retry_threshold


def decode_output(output_bytes: bytes) -> str:
    """Attempt to decode byte strings with common encodings."""

    encodings = ["utf-8", "gbk", "cp936"]
    for enc in encodings:
        try:
            return output_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return output_bytes.decode("utf-8", errors="replace")


def execute_command(command: str, cwd: str) -> tuple[bool, str]:
    """Execute a command and return its output."""

    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
        )
        stdout_bytes, stderr_bytes = process.communicate()
        stdout = decode_output(stdout_bytes)
        stderr = decode_output(stderr_bytes)

        if process.returncode == 0:
            return True, stdout
        error_output = stderr if stderr.strip() else stdout
        return False, error_output.strip()
    except Exception as e:
        return False, str(e)

agent = Agent(api_slot_name=Agent.setting_api)
console = agent.console
session = agent.session
check_result = agent.check_result

if __name__ == "__main__":
    user_input = ""
    while True:
        try:
            if session.awaiting_user_input:
                prompt_text = "[bold blue]" + f" {session.cwd} Smart_Shell> " + "[/bold blue]"
                user_input = Prompt.ask(prompt_text)

                if user_input.lower() in ["/exit", "exit", "quit"]:
                    console.print("[yellow]Goodbye![/yellow]")
                    break

                if user_input.strip().startswith("/cd "):
                    path = user_input.strip().split(" ", 1)[1]
                    _, message = session.change_directory(path)
                    console.print(message)
                    continue

                session.add_user(user_input)
                session.advance_state(SessionContext.State.AWAITING_MODEL_RESPONSE)
                continue

            reply, _ = get_chat_response(agent)

            try:
                pattern = re.compile(r"```(?:json)?\n(.*?)\n```", re.S)
                if pattern.search(reply):
                    reply = pattern.findall(reply)[0]
                command = json.loads(reply)
                session.add_assistant(reply)
                session.reset_retry_count()

                action = command.get("action")

                if action == "execute_command":
                    console.print(
                        f"[bold yellow]Executing command:[/bold yellow] {command.get('command', '')}"
                    )
                    console.print(f"[dim]{command.get('explanation', '')}[/dim]")

                    confirm_prompt = "Execute command?"
                    confirm = Prompt.ask(confirm_prompt, choices=["y", "n"], default="n")

                    if confirm == "y":
                        cmd_to_run_raw = command.get("command")
                        cmd_to_run = str(cmd_to_run_raw).strip() if cmd_to_run_raw is not None else ""
                        if not cmd_to_run:
                            console.print("[red]No executable command provided. Ignored.[/red]")
                            session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
                            continue

                        run_success, result = execute_command(cmd_to_run, str(session.cwd))
                        print("\n" + result)

                        verification = check_result(user_input, result)
                        console.print(f"[dim]Verification result {verification}[/dim]")

                        if not run_success:
                            console.print("[yellow]Command returned a non-zero exit code.[/yellow]")

                        session.add_assistant(result + "\n Verification result: " + verification)
                        session.add_user(
                            "How did the tool invocation go? Please provide a brief summary using the direct reply template."
                        )
                        session.advance_state(SessionContext.State.AWAITING_MODEL_RESPONSE)
                        continue
                    else:
                        console.print("[yellow]Execution cancelled[/yellow]")
                        session.add_assistant("Execution cancelled")
                        session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
                        continue

                elif action == "direct_reply":
                    md = Markdown(command.get("content", ""))
                    console.print(Panel(md, title="Reply", border_style="blue"))
                    session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
                    continue
                else:
                    console.print(f"[red]Unknown action: {command.get('action')}[/red]")
                    session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
                    continue

            except json.JSONDecodeError:
                console.print(f"[red]Unable to parse the response:[/red]\n {reply}")
                session.add_system(
                    "Please respond in JSON format without any markdown markers from now on."
                )
                session.register_retry_failure()
                session.advance_state(SessionContext.State.AWAITING_MODEL_RESPONSE)
                if session.has_exceeded_retry_threshold():
                    console.print("[red][!] Too many parsing failures, exiting![/red]")
                    break

        except KeyboardInterrupt:
            console.print("\n[yellow]Use /exit to quit the program[/yellow]")
            if not session.awaiting_user_input:
                session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
            continue
        except Exception as error:
            console.print(f"[red]An error occurred:[/red] {str(error)}")
            if not session.awaiting_user_input:
                session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
            continue
