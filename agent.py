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
assert API_CONFIG["url"] != "your_url" and API_CONFIG["api_key"] != "sk-xxx", "请填写正确的url和api_key"

# System prompt for the agent
SYSTEM_PROMPT = """
你是一个Linux命令终端Agent,需要判断用户是否需要执行终端命令。按规则3,使用JSON格式生成回答;

规则：
1. 当用户请求涉及文件操作、系统状态查询、进程管理时,生成命令。保证在bash里执行不会出错。
2. 危险命令(rm -rf、sudo等)需向用户二次确认
3. 命令格式示例：
{
  "action": "execute_command", 
  "command": "dir",
  "explanation": "列出当前目录的详细信息"
}
或正常回答示例:
{
  "action": "direct_reply",
  "content": "好的,已为您查询到..."
}
4. 不要直接回答问题,请遵守规则3,按JSON格式回答。
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
    """执行命令并保留颜色输出"""
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
            rejudge = False
            user_input = Prompt.ask("[bold blue]Smart_Shell[/bold blue]")
            
            if user_input.lower() in ['/quit', 'exit', 'quit']:
                console.print("[yellow]再见！[/yellow]")
                break
                
            payload.append({"role": "user", "content": user_input})
            
        response = client.chat.completions.create(
            model=API_CONFIG["model"], messages=payload, stream=True
        )
        
        replay = ""
        with console.status("[bold green]思考中...[/bold green]"):
            for chunk in response:
                replay += chunk.choices[0].delta.content
                
        try:
            command = json.loads(replay)
            payload.append({"role": "assistant", "content": replay})
            
            if command["action"] == "execute_command":
                console.print(f"[bold yellow]执行指令:[/bold yellow] {command['command']}")
                console.print(f"[dim]{command.get('explanation', '')}[/dim]")
                
                confirm = Prompt.ask("是否执行?", choices=["y", "n"], default="n")
                
                if confirm == "y":
                    success, result = execute_command(command["command"])
                    print("\n" + result)
                    
                    if success:
                        payload.append({"role": "assistant", "content": result})
                    else:
                        console.print(f"[red]执行失败:[/red] {result}")
                        payload.append(
                            {"role": "assistant", "content": f"执行失败: {result}"}
                        )
                else:
                    console.print("[yellow]已取消执行[/yellow]")
                    payload.append({"role": "assistant", "content": "已取消执行"})
                    
            elif command["action"] == "direct_reply":
                # Display direct reply with proper Markdown formatting
                md = Markdown(command["content"])
                console.print(Panel(md, title="回复", border_style="blue"))
                
        except json.JSONDecodeError:
            console.print(f"[red]无法解析结果:[/red]\n {replay}")
            payload.append({"role": "user", "content": "接下来请只用JSON格式回复"})
            rejudge = True
            
    except KeyboardInterrupt:
        console.print("\n[yellow]使用 /quit 退出程序[/yellow]")
        continue
    except Exception as e:
        console.print(f"[red]发生错误:[/red] {str(e)}")
        continue
