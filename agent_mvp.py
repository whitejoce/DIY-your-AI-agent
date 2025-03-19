#!/usr/bin/env python
# _*_coding: utf-8 _*_
# Coder:Whitejoce

from openai import OpenAI
import json, os ,re

url = "your_url"
api_key = "sk-xxxx"
model = "Qwen/Qwen2.5-7B-Instruct"

assert url != "your_url" and api_key != "sk-xxxx", "请填写正确的url和api_key"

client = OpenAI(api_key=api_key, base_url=url)
prompt = """
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

def process_response(model, payload):
    response = client.chat.completions.create(model=model, messages=payload, stream=True)
    reply_chunk, reasoning_chunk = [], []

    for chunk in response:
        if chunk.choices[0].delta.content:
            reply_chunk.append(chunk.choices[0].delta.content)
        if chunk.choices[0].delta.reasoning_content:
            reasoning_chunk.append(chunk.choices[0].delta.reasoning_content)
            print(chunk.choices[0].delta.reasoning_content, end="")

    reply = "".join(reply_chunk)
    reasoning = "".join(reasoning_chunk)
    return reply, reasoning


payload = [{"role": "system", "content": prompt}]
rejudge = False
rejudge_count = 0
while True:
    if not rejudge:
        user_input = input("\033[1;36mSmart_Shell> \033[0m")
        if user_input == r"/quit":
            break
        payload.append({"role": "user", "content": user_input})
    reply, reasoning = process_response(model,payload)
    try:
        pattern = re.compile(r"```json\n(.*?)\n```", re.S)
        if pattern.search(reply):
            reply = pattern.findall(reply)[0]
        command = json.loads(reply)
        rejudge = False
        rejudge_count = 0
        payload.append({"role": "assistant", "content": reply})
        if command["action"] == "execute_command":
            print(f" [+] 执行指令: {command['command']}")
            confirm = input("是否执行? (y/n): ")
            if confirm == "y":
                result = os.popen(command["command"]).read()
                print(f"{result=}")
                ret_val = os.popen("echo $?").read()
                if ret_val == "0\n":
                    payload.append({"role": "assistant", "content": result})
                else:
                    payload.append(
                        {"role": "assistant", "content": f"执行失败: {result}"}
                    )
            else:
                payload.append({"role": "assistant", "content": "已取消执行"})
        elif command["action"] == "direct_reply":
            print(" [=] "+command["content"])
    except json.JSONDecodeError:
        print(f" [!] 无法解析结果:\n {reply=}")
        payload.append({"role": "user", "content": "回答格式错误,你应该使用JSON,并且避免任何markdown标记。请重新按照要求回答问题"})
        rejudge = True
        rejudge_count += 1
        if rejudge_count > 3:
            print(" [!] 无法解析结果次数过多，程序退出")
            break