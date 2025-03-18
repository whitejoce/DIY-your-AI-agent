#!/usr/bin/env python
# _*_coding: utf-8 _*_
# Coder: Whitejoce

import json
import subprocess

from openai import OpenAI
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown

# Configuration
API_CONFIG = {
    "url": "your_url",
    "api_key": "sk-xxx",  # Add your API key here
    "model": "Qwen/Qwen2.5-7B-Instruct"
}

# Validate API configuration
assert API_CONFIG["url"] != "your_url" and API_CONFIG["api_key"] != "sk-xxx", "Please provide a valid URL and API key"

# System prompt for the agent
SYSTEM_PROMPT = """
You are a Linux command terminal Agent. You need to determine whether the user requires terminal command execution. Follow Rule 3 and generate responses in JSON format;

Rules:
1. When the user's request involves file operations, system status queries, or process management, generate commands. Ensure the commands can be executed in bash without errors.
2. Dangerous commands (e.g., rm -rf, sudo) require secondary confirmation from the user.
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
4. Do not directly answer questions. Follow Rule 3 and respond in JSON format.
"""

# Initialize Rich components
console = Console()

# Initialize OpenAI client
client = OpenAI(
    api_key=API_CONFIG["api_key"], 
    base_url=API_CONFIG["url"]
)

payload = [{"role": "system", "content": SYSTEM_PROMPT}]

def execute_command(cmd):
    """Execute a command and retain colored output"""
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            return True, stdout
        else:
            return False, stderr
    except Exception as e:
        return False, str(e)

rejudge = False
while True:
    try:
        if not rejudge:
            user_input = Prompt.ask("[bold blue]Smart_Shell[/bold blue]")
            
            if user_input.lower() in ['/quit', 'exit', 'quit']:
                console.print("[yellow]Goodbye![/yellow]")
                break
                
            payload.append({"role": "user", "content": user_input})
        rejudge = False
        response = client.chat.completions.create(
            model=API_CONFIG["model"], messages=payload, stream=True
        )
        
        replay = ""
        with console.status("[bold green]Thinking...[/bold green]"):
            for chunk in response:
                replay += chunk.choices[0].delta.content
                
        try:
            command = json.loads(replay)
            payload.append({"role": "assistant", "content": replay})
            
            if command["action"] == "execute_command":
                console.print(f"[bold yellow]Executing command:[/bold yellow] {command['command']}")
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
                            {"role": "assistant", "content": f"Execution failed: {result}"}
                        )
                else:
                    console.print("[yellow]Execution canceled[/yellow]")
                    payload.append({"role": "assistant", "content": "Execution canceled"})
                    
            elif command["action"] == "direct_reply":
                # Display direct reply with proper Markdown formatting
                md = Markdown(command["content"])
                console.print(Panel(md, title="Reply", border_style="blue"))
                
        except json.JSONDecodeError:
            console.print(f"[red]Unable to parse result:[/red]\n {replay}")
            payload.append({"role": "user", "content": "Please respond in JSON format only from now on"})
            rejudge = True
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Use /quit to exit the program[/yellow]")
        continue
    except Exception as e:
        console.print(f"[red]An error occurred:[/red] {str(e)}")
        continue
