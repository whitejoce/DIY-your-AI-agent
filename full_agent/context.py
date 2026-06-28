import json
from typing import Any, Dict, List


class ConversationMemory:
    def __init__(self):
        self.messages = []

    def add_user(self, content):
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content):
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_call(self, tool_call):
        self.messages.append(tool_call.to_response_message())

    def add_tool_output(self, call_id, output):
        self.messages.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": output,
            }
        )

    def all(self):
        return list(self.messages)


class ContextManager:
    def __init__(self, budget_chars):
        self.budget_chars = budget_chars

    def build_input(self, system_prompt, messages, skill_instructions=""):
        prompt = system_prompt
        if skill_instructions:
            prompt = prompt + "\n\nRelevant skill instructions:\n" + skill_instructions

        system_message = {"role": "system", "content": prompt}
        trimmed = self._trim_messages(list(messages), self.budget_chars - self._size(system_message))
        return [system_message] + trimmed

    def _trim_messages(self, messages, budget):
        if budget <= 0:
            return []
        trimmed = list(messages)
        while trimmed and self._size(trimmed) > budget:
            trimmed.pop(0)
        return trimmed

    def _size(self, value):
        return len(json.dumps(value, ensure_ascii=False))
