import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AgentConfig:
    model: str = "gpt-5.4-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_turns: int = 10
    max_tokens: int = 2048
    temperature: float = 0.2
    context_budget_chars: int = 24000
    memory_path: Path = field(default_factory=lambda: Path(".agent") / "memory.jsonl")
    skills_dir: Path = field(default_factory=lambda: Path(".agent") / "skills")
    show_tool_calls: bool = True

    def __post_init__(self):
        self.memory_path = Path(self.memory_path)
        self.skills_dir = Path(self.skills_dir)

    @classmethod
    def from_env(cls):
        return cls(
            model=os.getenv("MODEL") or cls.model,
            api_key=os.getenv("API_KEY") or None,
            base_url=os.getenv("BASE_URL") or None,
        )
