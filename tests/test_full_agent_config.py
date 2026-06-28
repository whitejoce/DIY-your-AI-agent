import full_agent.config as config_module
from full_agent.config import AgentConfig, ModelConfig


ENV_KEYS = [
    "MODEL_PROVIDER",
    "MODEL_API",
    "MODEL",
    "API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "BASE_URL",
    "MAX_TOKENS",
    "TEMPERATURE",
    "MAX_TURNS",
    "CONTEXT_BUDGET_CHARS",
    "MEMORY_PATH",
    "SKILLS_DIR",
    "SHOW_TOOL_CALLS",
]


def clear_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_agent_config_loads_dotenv_before_reading_values(tmp_path, monkeypatch):
    clear_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "MODEL_PROVIDER=openai",
                "MODEL_API=completions",
                "MODEL=test-model",
                "API_KEY=test-key",
                "BASE_URL=https://example.test/v1",
                "MAX_TOKENS=123",
                "TEMPERATURE=0.7",
                "MAX_TURNS=4",
                "CONTEXT_BUDGET_CHARS=9000",
                "SHOW_TOOL_CALLS=false",
            ]
        ),
        encoding="utf-8",
    )

    config = AgentConfig.from_env(env_file)

    assert config.model_provider == "openai"
    assert config.model_api == "chat_completions"
    assert config.model == "test-model"
    assert config.api_key == "test-key"
    assert config.base_url == "https://example.test/v1"
    assert config.max_tokens == 123
    assert config.temperature == 0.7
    assert config.max_turns == 4
    assert config.context_budget_chars == 9000
    assert config.show_tool_calls is False


def test_existing_environment_values_are_not_overwritten(tmp_path, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("MODEL", "from-environment")
    env_file = tmp_path / ".env"
    env_file.write_text("MODEL=from-file\nAPI_KEY=from-file-key", encoding="utf-8")

    config = AgentConfig.from_env(env_file)

    assert config.model == "from-environment"
    assert config.api_key == "from-file-key"


def test_model_config_can_read_provider_specific_api_keys(tmp_path, monkeypatch):
    clear_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MODEL_PROVIDER=anthropic\nANTHROPIC_API_KEY=anthropic-key",
        encoding="utf-8",
    )

    config = ModelConfig.from_env(env_file)

    assert config.provider == "anthropic"
    assert config.api_key == "anthropic-key"


def test_default_env_loading_uses_package_env_not_cwd(tmp_path, monkeypatch):
    clear_env(monkeypatch)
    package_dir = tmp_path / "full_agent"
    package_dir.mkdir()
    cwd = tmp_path / "project"
    cwd.mkdir()
    (package_dir / ".env").write_text(
        "MODEL=from-package\nAPI_KEY=package-key",
        encoding="utf-8",
    )
    (cwd / ".env").write_text(
        "MODEL=from-cwd\nAPI_KEY=cwd-key",
        encoding="utf-8",
    )
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(config_module, "__file__", str(package_dir / "config.py"))

    config = AgentConfig.from_env()

    assert config.model == "from-package"
    assert config.api_key == "package-key"


def test_agent_config_keeps_legacy_model_fields_usable():
    config = AgentConfig(
        model="legacy-model",
        model_api="completions",
        api_key="legacy-key",
        base_url="https://example.test/v1",
        max_tokens=99,
        temperature=0.3,
    )

    assert config.model_config.model == "legacy-model"
    assert config.model_config.api == "chat_completions"
    assert config.api_key == "legacy-key"
    assert config.base_url == "https://example.test/v1"
    assert config.max_tokens == 99
    assert config.temperature == 0.3
