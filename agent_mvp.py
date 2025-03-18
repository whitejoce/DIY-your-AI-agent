#!/usr/bin/env python
# _*_coding: utf-8 _*_
# Coder:Whitejoce

from openai import OpenAI
import json, os

url = "your_url"
api_key = "sk-xxxx"
model = "Qwen/Qwen2.5-7B-Instruct"

assert url != "your_url" and api_key != "sk-xxxx", "请填写正确的url和api_key"

client = OpenAI(api_key=api_key, base_url=url)
prompt = """
你是一个Linux助手Agent,需要判断用户是否需要执行终端命令。按规则3,使用JSON格式生成回答;

规则：
1. 当用户请求涉及文件操作、系统状态查询、进程管理时,生成命令。保证在bash里执行不会出错。
2. 危险命令(rm -rf、sudo等)需向用户二次确认
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
4. 不要直接回答问题,请遵守规则3,按JSON格式回答。
"""

payload = [{"role": "system", "content": prompt}]
rejudge = False
while True:
    if not rejudge:
        user_input = input("Smart_Shell> ")
        if user_input == r"/quit":
            break
    rejudge = False
    payload.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model=model, messages=payload, stream=True
    )
    replay = ""
    for chunk in response:
        replay += chunk.choices[0].delta.content
    try:
        command = json.loads(replay)
        payload.append({"role": "assistant", "content": replay})
        if command["action"] == "execute_command":
            print(f"执行指令: {command['command']}")
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
            print(command["content"])
    except json.JSONDecodeError:
        print(f"无法解析结果:\n {replay=}")
        payload.append({"role": "user", "content": "接下来请只用JSON格式回复"})
        rejudge = True
