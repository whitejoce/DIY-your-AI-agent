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

# API 配置
API_CONFIG = {
    "url": "your_url",
    "api_key": "",  # 填写你的API key
    "model": "Qwen/Qwen2.5-7B-Instruct",
}

# 验证API配置
assert (
    API_CONFIG["url"] != "your_url" and API_CONFIG["api_key"] != ""
), "请填写正确的url和api_key"

# 系统提示词
SYSTEM_PROMPT = """
你是一个Windows助手Agent,需要判断用户是否需要执行终端命令。请严格遵循以下规则,并且输出必须为纯JSON格式,无markdown标记
规则:

1.当用户的请求涉及文件操作、系统状态查询、进程管理等操作时,生成相应的终端命令,且确保命令在powershell环境下可以正确执行。
2.对于危险命令(例如:rm -rf、sudo等),必须要求用户进行二次确认后再执行。
3. 命令格式示例：
{
  "action": "execute_command", 
  "command": "ls -l",
  "explanation": "列出当前目录的详细信息"
}
或正常回答示例:
{
  "action": "direct_reply",
  "content": "好的,已为您查询到..."
}
4.请根据上述规则以符合格式的JSON进行回复。
"""

# 初始化Rich组件
console = Console()

# 初始化OpenAI客户端
client = OpenAI(api_key=API_CONFIG["api_key"], base_url=API_CONFIG["url"])

payload = [{"role": "system", "content": SYSTEM_PROMPT}]


def get_chat_response(client, payload):
    response = client.chat.completions.create(
        model=API_CONFIG["model"], messages=payload, stream=True
    )
    reply_chunk, reasoning_chunk = [], []
    has_reasoning = False
    with console.status("[bold green]思考中...[/bold green]") as status:
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                reply_chunk.append(content)
            
            if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                has_reasoning = True
                reasoning_content = chunk.choices[0].delta.reasoning_content
                reasoning_chunk.append(reasoning_content)
                status.stop()
                console.print(reasoning_content, end="")
                
    if has_reasoning:
        print()
        
    return "".join(reply_chunk), "".join(reasoning_chunk)


def execute_command(cmd):
    # 执行命令并保留颜色输出
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
                console.print("[yellow]再见！[/yellow]")
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
                    f"[bold yellow]执行指令:[/bold yellow] {command['command']}"
                )
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
                # 直接回复并Markdown格式化
                md = Markdown(command["content"])
                console.print(Panel(md, title="回复", border_style="blue"))

        except json.JSONDecodeError:
            console.print(f"[red]无法解析结果:[/red]\n {reply}")
            payload.append(
                {
                    "role": "system",
                    "content": "接下来请提供符合格式的回复,即使用JSON,并且避免任何markdown标记。",
                }
            )
            rejudge = True
            rejudge_count += 1
            if rejudge_count > 3:
                print(f"[red] [!] 无法解析结果次数过多，程序退出![/red]")
                break

    except KeyboardInterrupt:
        console.print("\n[yellow]使用 /quit 退出程序[/yellow]")
        continue
    except Exception as error:
        console.print(f"[red]发生错误:[/red] {str(error)}")
        continue
