#!/usr/bin/env python
# _*_coding: utf-8 _*_
#Coder:Whitejoce

from openai import OpenAI
import json,os

url = "your_url"
api_key = "sk-xxxx"
model = "Qwen/Qwen2.5-7B-Instruct"

assert url != "your_url" and api_key != "sk-xxxx", "Please provide the correct url and api_key."

client = OpenAI(api_key=api_key, base_url=url)
prompt = """
You are a Linux assistant agent. You must determine whether the user needs to execute terminal commands. According to rule #3, generate answers in JSON format;

Rules:
1. When the user’s request involves file operations, system status queries, or process management, generate commands. Ensure they can be executed in bash without errors.
2. Dangerous commands (rm -rf, sudo, etc.) require the user's secondary confirmation.
3. Command format example:
{
    "action": "execute_command",
    "command": "ls -l",
    "explanation": "List detailed information of the current directory"
}
Or normal answer example:
{
    "action": "direct_reply",
    "content": "Ok, I've found the information for you..."
}
4. Do not answer questions directly. Please follow rule #3 and respond in JSON format.
"""

payload = [{"role": "system", "content": prompt}]
rejudge = False
while True:
        if not rejudge:
            rejudge = False
            user_input = input("Smart_Shell> ")
            if user_input == r"/quit":
                    break
            payload.append({"role": "user", "content": user_input})
        response = client.chat.completions.create(
                model=model,
                messages=payload,
                stream=True
        )
        replay = ""
        for chunk in response:
                replay += chunk.choices[0].delta.content
        try:
                command = json.loads(replay)
                payload.append({"role": "assistant", "content": replay})
                if command["action"] == "execute_command":
                        print(f"Executing command: {command['command']}")
                        confirm = input("Execute? (y/n): ")
                        if confirm == "y":
                                result = os.popen(command['command']).read()
                                print(f"{result=}")
                                ret_val = os.popen("echo $?").read()
                                if ret_val == "0\n":
                                        payload.append({"role": "assistant", "content": result})
                                else:
                                        payload.append({"role": "assistant", "content": f"Execution failed: {result}"})
                        else:
                                payload.append({"role": "assistant", "content": "Execution canceled"})
                elif command["action"] == "direct_reply":
                        print(command["content"])
        except json.JSONDecodeError:
                print(f"Unable to parse result:\n {replay=}")
                payload.append({"role": "user", "content": "You should reply in JSON format"})
                rejudge = True
