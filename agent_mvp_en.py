#!/usr/bin/env python
# _*_coding: utf-8 _*_
# Coder:Whitejoce

from openai import OpenAI
import json, os, re

url = "your_url"
api_key = "sk-xxxx"
model = "Qwen/Qwen2.5-7B-Instruct"

assert url != "your_url" and api_key != "sk-xxxx", "Please fill in the correct url and api_key"

client = OpenAI(api_key=api_key, base_url=url)
prompt = """
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
            print(f" [+] Execute command: {command['command']}")
            confirm = input("Proceed with execution? (y/n): ")
            if confirm == "y":
                result = os.popen(command["command"]).read()
                print(f"{result=}")
                ret_val = os.popen("echo $?").read()
                if ret_val == "0\n":
                    payload.append({"role": "assistant", "content": result})
                else:
                    payload.append(
                        {"role": "assistant", "content": f"Execution failed: {result}"}
                    )
            else:
                payload.append({"role": "assistant", "content": "Execution cancelled"})
        elif command["action"] == "direct_reply":
            print(" [=] "+command["content"])
    except json.JSONDecodeError:
        print(f" [!] Unable to parse result:\n {reply=}")
        payload.append({"role": "user", "content": "Response format error, you should use JSON and avoid any markdown markup. Please answer the question again according to the requirements"})
        rejudge = True
        rejudge_count += 1
        if rejudge_count > 3:
            print(" [!] Response format error, exit!")
            break