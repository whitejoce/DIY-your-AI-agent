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

# API configuration
API_CONFIG = {
    "url": "your_url",
    "api_key": "",  # Enter your API key here
    "model": "Qwen/Qwen2.5-7B-Instruct",
}
# Validate API configuration
assert (
    API_CONFIG["url"] != "your_url" and API_CONFIG["api_key"] != ""
), "Please provide a valid url and api_key"

# System prompt
SYSTEM_PROMPT = """
You are a Linux terminal assistant Agent. Please strictly follow the rules below:

Rules:

1. When the user requests system operations, generate the corresponding terminal command (ensure Bash compatibility)
2. Dangerous commands must require secondary confirmation before execution
3. The output format must always be JSON, structured as follows:

{
  "action": "execute_command",
  "command": "ls -l",
  "explanation": "List detailed information of the current directory using the ls tool"
}

or

{
  "action": "direct_reply",
  "content": "Hello, how can I help you?"
}
"""

# Initialize Rich components
console = Console()

# Initialize OpenAI client
client = OpenAI(api_key=API_CONFIG["api_key"], base_url=API_CONFIG["url"])

payload = [{"role": "system", "content": SYSTEM_PROMPT}]

def check_result(model_client, user_input, command_output) -> str:
    prompt = f"""
You are a task verification assistant. Based on the following information, determine whether the command met the user's expectations.

User request: {user_input}
Command output: {command_output}

Please answer:
- If the expectation is met, output "[✅] Success"
- If not, output "[❌] Failure: Reason"
    """
    response = model_client.chat.completions.create(
        model=API_CONFIG["model"],
        messages=[{"role": "system", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def get_chat_response(client: OpenAI, payload: list[dict[str,str]]) -> tuple[str, str]:
    """Get chat response"""
    response = client.chat.completions.create(
        model=API_CONFIG["model"], messages=payload, stream=True
    )
    reply_chunk, reasoning_chunk = [], []
    full_reply = ""
    has_reasoning = False
    with console.status("[bold green]Thinking...[/bold green]") as status:
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                reply_chunk.append(content)
                full_reply += content
            
            if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                has_reasoning = True
                reasoning_content = chunk.choices[0].delta.reasoning_content
                reasoning_chunk.append(reasoning_content)
                status.stop()
                console.print(reasoning_content, end="")
                
    if has_reasoning:
        print()
        
    return "".join(reply_chunk), "".join(reasoning_chunk)

def decode_output(output_bytes: bytes) -> str:
    """Try to decode byte string using common encodings."""
    encodings = ['utf-8', 'gbk', 'cp936']  # Common encodings, especially for Windows
    for enc in encodings:
        try:
            return output_bytes.decode(enc)
        except UnicodeDecodeError:
            #print(f"Decoding with {enc} failed, trying next encoding...")
            continue
    # Default to UTF-8 with error replacement
    return output_bytes.decode('utf-8', errors='replace')


def execute_command(command: str) -> tuple[bool, str]:
    """Execute the command and return its output."""
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
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


rejudge = False
rejudge_count = 0

if __name__ == "__main__":
    while True:
        try:
            if not rejudge:
                rejudge = False
                user_input = Prompt.ask("[bold blue]Smart_Shell[/bold blue]")

                if user_input.lower() in ["/exit", "exit", "quit"]:
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

                        # Add verification logic
                        verification = check_result(client, user_input, result)
                        console.print(f"[dim]Verification result {verification}[/dim]")

                        payload.append({"role": "assistant", "content": result+ "\n Verification result: " +verification})
                        payload.append(
                            {
                                "role": "user",
                                "content": "How was the result of the tool execution? Please provide a brief summary using the direct reply template.",
                            }
                        )
                        rejudge = True  # Set the flag to let the LLM handle this summary request in the next round
                    else:
                        console.print("[yellow]Execution cancelled[/yellow]")
                        payload.append({"role": "assistant", "content": "Execution cancelled"})

                elif command["action"] == "direct_reply":
                    # Direct reply with Markdown formatting
                    md = Markdown(command["content"])
                    console.print(Panel(md, title="Reply", border_style="blue"))

            except json.JSONDecodeError:
                console.print(f"[red]Unable to parse result:[/red]\n {reply}")
                payload.append(
                    {
                        "role": "system",
                        "content": "Please provide a reply in the correct format (JSON only, no markdown tags).",
                    }
                )
                rejudge = True
                rejudge_count += 1
                if rejudge_count > 3:
                    print(f"[red] [!] Too many parsing failures, exiting![/red]")
                    break

        except KeyboardInterrupt:
            console.print("\n[yellow]Use /exit to quit the program[/yellow]")
            continue
        except Exception as error:
            console.print(f"[red]Error occurred:[/red] {str(error)}")
            continue

