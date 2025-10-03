#!/usr/bin/env python
# _*_coding: utf-8 _*_
# Coder: Whitejoce
# use GPT-5 Codex optimized

import re, json
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
    """统一管理Agent的状态(API,Prompt)和操作(max_retry_count)。"""

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
        }
    }
    setting_api = "openai"  # 默认的api slot名称
    def __init__(self, api_slot_name: str, max_turns: int = 20):
        self.console = Console()
        self.api_config = self._setup_api_config(api_slot_name)
        self.client = OpenAI(api_key=self.api_config["api_key"], base_url=self.api_config["url"])
        self.session = SessionContext(system_prompt=self.SYSTEM_PROMPT, max_turns=max_turns)
    SYSTEM_PROMPT = """
    你是一个 Linux 终端助手 Agent,请严格遵循以下规则：
    1. 当用户请求涉及系统操作时，生成相应终端命令,直接回复用户问题时,使用Markdown格式化
    2. 危险命令必须要求二次确认后再执行
    3. 一次只能执行一个命令
    4. 如果用户告诉你切换到指定目录，请告知用户使用 /cd 命令切换目录
    5. 输出格式始终为 JSON,结构如下:
    {
        "action": "execute_command",
        "command": "ls -l",
        "explanation": "通过ls工具列出当前目录的详细信息"
    }
    或
    {
        "action": "direct_reply",
        "content": "你好，有什么我可以帮助你的吗？"
    }
    """.strip()
    def _setup_api_config(self, api_slot_name: str) -> dict:
        """根据名称配置和验证API。"""
        
        config = self.API_SLOTS.get(api_slot_name)
        if not config:
            raise ValueError(f"API slot '{api_slot_name}' not found.")
        #import base64
        # Decode API key if it's base64 encoded
        # try:
        #     config['api_key'] = base64.b64decode(config['api_key']).decode('utf-8')
        # except (Exception):
        #     # Not a valid base64 string, use as is.
        #     pass

        assert (
            config["url"] != "your_url" and config["api_key"] != "your_api_key"
        ), "请填写正确的url和api_key"
        return config

    def check_result(self, user_input: str, command_output: str) -> str:
        """验证命令输出是否符合用户预期。"""
        prompt = f"""
        你是一个任务验证助手，请根据以下信息判断命令是否达到了用户的预期。

        用户请求: {user_input}
        命令输出: {command_output}

        请回答:
        - 如果达到了预期，输出 "[✅] 成功"
        - 如果未达到预期，输出 "[❌] 失败: 原因说明"
        """.strip()
        response = self.client.chat.completions.create(
            model=self.api_config["model"],
            messages=[{"role": "system", "content": prompt}]
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""

@dataclass
class SessionContext:
    """SessionContext 统一维护 shell 状态、聊天记录与有限状态机。"""
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

    # --- 聊天记录管理 ---
    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self._trim_history()

    def add_user(self, content: str):
        self.add_message("user", content)

    def add_assistant(self, content: str):
        self.add_message("assistant", content)

    def add_system(self, content: str):
        self.add_message("system", content)

    # 限制聊天记录长度为 max_turns * 2
    def _trim_history(self):
        if self.max_turns <= 0:
            return
        max_messages = self.max_turns * 2
        overflow = len(self.messages) - 1 - max_messages
        if overflow > 0:
            del self.messages[1:1 + overflow]

    def as_payload(self) -> List[Dict[str, str]]:
        return [msg.copy() for msg in self.messages]

    # --- shell 状态管理 ---
    @property
    def cwd(self) -> pathlib.Path:
        return pathlib.Path.cwd()

    def change_directory(self, path: str) -> tuple[bool, str]:
        try:
            target_path = pathlib.Path(path).expanduser()
            os.chdir(target_path)
            return True, f"已切换到目录: {os.getcwd()}"
        except FileNotFoundError:
            return False, f"[red]错误: 目录 '{path}' 不存在。[/red]"
        except Exception as e:
            return False, f"[red]切换目录时发生错误: {e}[/red]"

    # --- 状态机 ---
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


def get_chat_response(agent: Agent) -> tuple[str, str]:
    """获取聊天响应"""
    response = agent.client.chat.completions.create(
        model=agent.api_config["model"],
        messages=agent.session.as_payload(),  # type: ignore[arg-type]
        stream=True,
    )
    reply_chunk, reasoning_chunk = [], []
    has_reasoning = False
    with console.status("[bold green]思考中...[/bold green]") as status:
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                reply_chunk.append(content)

            if reasoning_content := getattr(chunk.choices[0].delta, "model_extra", {}).get("reasoning_content"):
                has_reasoning = True
                reasoning_chunk.append(reasoning_content)
                status.stop()
                console.print(reasoning_content, end="")

    if has_reasoning:
        print()
    return "".join(reply_chunk), "".join(reasoning_chunk)

def decode_output(output_bytes: bytes) -> str:
    """尝试使用常见编码解码字节字符串。"""
    encodings = ['utf-8', 'gbk', 'cp936']  # 常见编码，尤其适用于Windows
    for enc in encodings:
        try:
            return output_bytes.decode(enc)
        except UnicodeDecodeError:
            #print(f"使用 {enc} 解码失败，尝试下一个编码...")
            continue
    # 默认UTF-8解码，使用替换错误处理
    return output_bytes.decode('utf-8', errors='replace')


def execute_command(command: str, cwd: str ) -> tuple[bool, str]:
    """执行command命令并返回输出。"""
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd
        )
        stdout_bytes, stderr_bytes = process.communicate()
        stdout = decode_output(stdout_bytes)
        stderr = decode_output(stderr_bytes)

        if process.returncode == 0:
            return True, stdout
        else:
            error_output = stderr if stderr.strip() else stdout
            return False, error_output.strip()
    except Exception as e:
        return False, str(e)
    
# 初始化Agent
agent = Agent(api_slot_name=Agent.setting_api)
console = agent.console
session = agent.session
check_result = agent.check_result

if __name__ == "__main__":
    user_input = ""
    while True:
        try:
            if session.awaiting_user_input:
                prompt = "[bold blue]" + f" {session.cwd} Smart_Shell> " + "[/bold blue]"
                user_input = Prompt.ask(prompt)

                if user_input.lower() in ["/exit", "exit", "quit"]:
                    console.print("[yellow]再见！[/yellow]")
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
                        f"[bold yellow]执行指令:[/bold yellow] {command.get('command', '')}"
                    )
                    console.print(f"[dim]{command.get('explanation', '')}[/dim]")

                    confirm_prompt = "是否执行?"
                    confirm = Prompt.ask(confirm_prompt, choices=["y", "n"], default="n")

                    if confirm == "y":
                        cmd_to_run_raw = command.get("command")
                        cmd_to_run = str(cmd_to_run_raw).strip() if cmd_to_run_raw is not None else ""
                        if not cmd_to_run:
                            console.print("[red]未提供可执行命令，已忽略。[/red]")
                            session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
                            continue

                        run_success, result = execute_command(cmd_to_run, str(session.cwd))
                        print("\n" + result)

                        verification = check_result(user_input, result)
                        console.print(f"[dim]验证结果 {verification}[/dim]")

                        if not run_success:
                            console.print("[yellow]命令返回非零退出码。[/yellow]")

                        session.add_assistant(result + "\n 验证结果: " + verification)
                        session.add_user(
                            "工具调用结果如何？请给出简要总结,使用直接回复模板回复。"
                        )
                        session.advance_state(SessionContext.State.AWAITING_MODEL_RESPONSE)
                        continue
                    else:
                        console.print("[yellow]已取消执行[/yellow]")
                        session.add_assistant("已取消执行")
                        session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
                        continue

                elif action == "direct_reply":
                    md = Markdown(command.get("content", ""))
                    console.print(Panel(md, title="回复", border_style="blue"))
                    session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
                    continue
                else:
                    console.print(f"[red]未知的 action: {command.get('action')}[/red]")
                    session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
                    continue

            except json.JSONDecodeError:
                console.print(f"[red]无法解析结果:[/red]\n {reply}")
                session.add_system(
                    "接下来请提供符合格式的回复,即使用JSON,并且避免任何markdown标记。"
                )
                session.register_retry_failure()
                session.advance_state(SessionContext.State.AWAITING_MODEL_RESPONSE)
                if session.has_exceeded_retry_threshold():
                    console.print("[red][!] 无法解析结果次数过多，程序退出![/red]")
                    break

        except KeyboardInterrupt:
            console.print("\n[yellow]使用 /exit 退出程序[/yellow]")
            if not session.awaiting_user_input:
                session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
            continue
        except Exception as error:
            console.print(f"[red]发生错误:[/red] {str(error)}")
            if not session.awaiting_user_input:
                session.advance_state(SessionContext.State.AWAITING_USER_INPUT)
            continue
