import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def _env_int(name, default):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _env_float(name, default):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


def _env_bool(name, default):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_env_files(env_file=None):
    if env_file is not None:
        candidates = [Path(env_file)]
    else:
        candidates = [Path(__file__).resolve().parent / ".env"]

    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen or not candidate.exists():
            continue
        seen.add(candidate)
        load_dotenv(candidate, override=False)


def _normalize_provider(provider):
    return provider.strip().lower().replace("-", "_")


def _normalize_model_api(api):
    normalized = api.strip().lower().replace("-", "_")
    aliases = {
        "response": "responses",
        "responses": "responses",
        "chat": "chat_completions",
        "chat_completion": "chat_completions",
        "chat_completions": "chat_completions",
        "completion": "chat_completions",
        "completions": "chat_completions",
        "anthropic": "anthropic_messages",
        "anthropic_message": "anthropic_messages",
        "anthropic_messages": "anthropic_messages",
        "messages": "anthropic_messages",
    }
    return aliases.get(normalized, normalized)


@dataclass
class ModelConfig:
    provider: str = "openai"
    api: str = "responses"
    model: str = "gpt-5.4-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.2

    def __post_init__(self):
        self.provider = _normalize_provider(self.provider)
        self.api = _normalize_model_api(self.api)

    @classmethod
    def from_env(cls, env_file=None):
        _load_env_files(env_file)
        defaults = cls()
        provider = _normalize_provider(os.getenv("MODEL_PROVIDER") or defaults.provider)
        api_key = os.getenv("API_KEY") or None
        if api_key is None:
            if provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY") or None
            else:
                api_key = os.getenv("OPENAI_API_KEY") or None

        return cls(
            provider=provider,
            api=os.getenv("MODEL_API") or defaults.api,
            model=os.getenv("MODEL") or defaults.model,
            api_key=api_key,
            base_url=os.getenv("BASE_URL") or None,
            max_tokens=_env_int("MAX_TOKENS", defaults.max_tokens),
            temperature=_env_float("TEMPERATURE", defaults.temperature),
        )


@dataclass(init=False)
class AgentConfig:
    model_config: ModelConfig
    max_turns: int
    context_budget_chars: int
    memory_path: Path
    skills_dir: Path
    show_tool_calls: bool

    def __init__(
        self,
        model_config=None,
        model=None,
        model_provider=None,
        model_api=None,
        api_key=None,
        base_url=None,
        max_tokens=None,
        temperature=None,
        max_turns=10,
        context_budget_chars=24000,
        memory_path=None,
        skills_dir=None,
        show_tool_calls=True,
    ):
        model_config = (
            replace(model_config) if model_config is not None else ModelConfig()
        )
        if model is not None:
            model_config.model = model
        if model_provider is not None:
            model_config.provider = model_provider
        if model_api is not None:
            model_config.api = model_api
        if api_key is not None:
            model_config.api_key = api_key
        if base_url is not None:
            model_config.base_url = base_url
        if max_tokens is not None:
            model_config.max_tokens = max_tokens
        if temperature is not None:
            model_config.temperature = temperature
        model_config.__post_init__()

        self.model_config = model_config
        self.max_turns = max_turns
        self.context_budget_chars = context_budget_chars
        self.memory_path = Path(memory_path or Path(".agent") / "memory.jsonl")
        self.skills_dir = Path(skills_dir or Path(".agent") / "skills")
        self.show_tool_calls = show_tool_calls

    @property
    def model(self):
        return self.model_config.model

    @model.setter
    def model(self, value):
        self.model_config.model = value

    @property
    def model_provider(self):
        return self.model_config.provider

    @model_provider.setter
    def model_provider(self, value):
        self.model_config.provider = _normalize_provider(value)

    @property
    def model_api(self):
        return self.model_config.api

    @model_api.setter
    def model_api(self, value):
        self.model_config.api = _normalize_model_api(value)

    @property
    def api_key(self):
        return self.model_config.api_key

    @api_key.setter
    def api_key(self, value):
        self.model_config.api_key = value

    @property
    def base_url(self):
        return self.model_config.base_url

    @base_url.setter
    def base_url(self, value):
        self.model_config.base_url = value

    @property
    def max_tokens(self):
        return self.model_config.max_tokens

    @max_tokens.setter
    def max_tokens(self, value):
        self.model_config.max_tokens = value

    @property
    def temperature(self):
        return self.model_config.temperature

    @temperature.setter
    def temperature(self, value):
        self.model_config.temperature = value

    @classmethod
    def from_env(cls, env_file=None):
        defaults = cls()
        return cls(
            model_config=ModelConfig.from_env(env_file),
            max_turns=_env_int("MAX_TURNS", defaults.max_turns),
            context_budget_chars=_env_int(
                "CONTEXT_BUDGET_CHARS", defaults.context_budget_chars
            ),
            memory_path=Path(os.getenv("MEMORY_PATH") or defaults.memory_path),
            skills_dir=Path(os.getenv("SKILLS_DIR") or defaults.skills_dir),
            show_tool_calls=_env_bool("SHOW_TOOL_CALLS", defaults.show_tool_calls),
        )
