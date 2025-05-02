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
你是一个 Linux 终端助手 Agent,请严格遵循以下规则：

规则:

1. 当用户请求涉及系统操作时，生成相应终端命令（确保兼容 Bash 环境）
2. 危险命令必须要求二次确认后再执行
3. 输出格式始终为 JSON,结构如下:

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
"""

# 初始化Rich组件
console = Console()

# 初始化OpenAI客户端
client = OpenAI(api_key=API_CONFIG["api_key"], base_url=API_CONFIG["url"])

payload = [{"role": "system", "content": SYSTEM_PROMPT}]

def check_result(model_client, user_input, command_output) -> str:
    prompt = f"""
你是一个任务验证助手，请根据以下信息判断命令是否达到了用户的预期。

用户请求: {user_input}
命令输出: {command_output}

请回答:
- 如果达到了预期，输出 "[✅] 成功"
- 如果未达到预期，输出 "[❌] 失败: 原因说明"
    """
    response = model_client.chat.completions.create(
        model=API_CONFIG["model"],
        messages=[{"role": "system", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def get_chat_response(client: OpenAI, payload: list[dict[str,str]]) -> tuple[str, str]:
    """获取聊天响应"""
    response = client.chat.completions.create(
        model=API_CONFIG["model"], messages=payload, stream=True
    )
    reply_chunk, reasoning_chunk = [], []
    full_reply = ""
    has_reasoning = False
    with console.status("[bold green]思考中...[/bold green]") as status:
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


def execute_command(command: str) -> tuple[bool, str]:
    """执行command命令并返回输出。"""
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
                    console.print("[yellow]再见！[/yellow]")
                    break

                payload.append({"role": "user", "content": user_input})

            reply, reasoning = get_chat_response(client, payload)

            try:
                pattern = re.compile(r"```(?:json)?\n(.*?)\n```", re.S)
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

                        # 添加验证逻辑
                        verification = check_result(client, user_input, result)
                        console.print(f"[dim]验证结果 {verification}[/dim]")

                        payload.append({"role": "assistant", "content": result+ "\n 验证结果: " +verification})
                        payload.append(
                            {
                                "role": "user",
                                "content": "工具调用结果如何？请给出简要总结,使用直接回复模板回复。",
                            }
                        )
                        rejudge = True # 设置标志，让LLM在下一轮处理这个总结请求
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
            console.print("\n[yellow]使用 /exit 退出程序[/yellow]")
            continue
        except Exception as error:
            console.print(f"[red]发生错误:[/red] {str(error)}")
            continue
