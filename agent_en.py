#!/usr/bin/env python
#!/usr/bin/env python
# _*_coding: utf-8 _*_
# Coder: Whitejoce

import re, json
import subprocess

from openai import OpenAI
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown

# Configuration
API_CONFIG = {
    "url": "your_url",
    "api_key": "",  # Add your API key here
    "model": "Qwen/Qwen2.5-7B-Instruct",
}

# Validate API configuration
assert (
    API_CONFIG["url"] != "your_url" and API_CONFIG["api_key"] != ""
), "Please fill in the correct url and api_key"

# System prompt for the agent
SYSTEM_PROMPT = """
You are a Linux Assistant Agent, you need to determine if the user needs to execute terminal commands. Please strictly follow these rules, and the output must be in pure JSON format without any markdown markup.
Rules:

1. When the user's request involves file operations, system status queries, process management, etc., generate the corresponding terminal commands that can be executed correctly in a bash environment.
2. For dangerous commands (e.g., rm -rf, sudo, etc.), you must ask the user for confirmation before executing.
3. Command format example:
{
  "action": "execute_command",
  "command": "ls -l",
  "explanation": "List detailed information of the current directory"
}
Or normal reply example:
{
  "action": "direct_reply",
  "content": "Okay, I have found the information for you..."
}
4. Don't answer questions directly, but respond according to the above rules with JSON in the correct format.
"""

# Initialize Rich components
console = Console()

# Initialize OpenAI client
client = OpenAI(api_key=API_CONFIG["api_key"], base_url=API_CONFIG["url"])

payload = [{"role": "system", "content": SYSTEM_PROMPT}]


def get_chat_response(client, payload):
    response = client.chat.completions.create(
        model=API_CONFIG["model"], messages=payload, stream=True
    )
    reply_chunk, reasoning_chunk = [], []
    for chunk in response:
        if chunk.choices[0].delta.content:
            reply_chunk.append(chunk.choices[0].delta.content)
        if chunk.choices[0].delta.reasoning_content:
            reasoning_chunk.append(chunk.choices[0].delta.reasoning_content)
            print(chunk.choices[0].delta.reasoning_content, end="")
    return "".join(reply_chunk), "".join(reasoning_chunk)


def execute_command(cmd):
    # Execute the command and keep the color output
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            return True, stdout
        else:
            return False, stderr
    except Exception as e:
        return False, str(e)


rejudge = False
rejudge_count = 0
while True:
    try:
        if not rejudge:
            rejudge = False
            user_input = Prompt.ask("[bold blue]Smart_Shell[/bold blue]")

            if user_input.lower() in ["/quit", "exit", "quit"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            payload.append({"role": "user", "content": user_input})

        reply, reasoning = get_chat_response(client, payload)

        try:
            pattern = re.compile(r"```json\n(.*?)\n```", re.S)
            if pattern.search(reply):
                reply = pattern.findall(reply)[0]
            command = json.loads(reply)
            payload.append({"role": "assistant", "content": reply})
            rejudge = False
            rejudge_count = 0
            if command["action"] == "execute_command":
                console.print(
                    f"[bold yellow]Executing command:[/bold yellow] {command['command']}"
                )
                console.print(f"[dim]{command.get('explanation', '')}[/dim]")

                confirm = Prompt.ask("Execute?", choices=["y", "n"], default="n")

                if confirm == "y":
                    success, result = execute_command(command["command"])
                    print("\n" + result)

                    if success:
                        payload.append({"role": "assistant", "content": result})
                    else:
                        console.print(f"[red]Execution failed:[/red] {result}")
                        payload.append(
                            {
                                "role": "assistant",
                                "content": f"Execution failed: {result}",
                            }
                        )
                else:
                    console.print("[yellow]Execution cancelled[/yellow]")
                    payload.append(
                        {"role": "assistant", "content": "Execution cancelled"}
                    )

            elif command["action"] == "direct_reply":
                md = Markdown(command["content"])
                console.print(Panel(md, title="Reply", border_style="blue"))

        except json.JSONDecodeError:
            console.print(f"[red]Unable to parse the result:[/red]\n {reply}")
            payload.append(
                {
                    "role": "system",
                    "content": "Please provide a response in the correct format using JSON and avoid any markdown markup.",
                }
            )
            rejudge = True
            rejudge_count += 1
            if rejudge_count > 3:
                print(
                    "[red] [!] Unable to parse the result too many times, exiting![/red]"
                )
                break

    except KeyboardInterrupt:
        console.print("\n[yellow]Use /quit to exit[/yellow]")
        continue
    except Exception as error:
        console.print(f"[red]An error occurred:[/red] {str(error)}")
        continue
