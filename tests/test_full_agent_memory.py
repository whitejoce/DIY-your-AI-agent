from full_agent.memory import MemoryRecord, MemoryStore
from full_agent.tools.memory_tools import MemoryToolProvider


def test_memory_store_adds_jsonl_record(tmp_path):
    store = MemoryStore(tmp_path / "memory.jsonl")

    record = store.add(MemoryRecord(content="Use Chinese by default", scope="user"))

    assert record["content"] == "Use Chinese by default"
    assert record["scope"] == "user"
    assert store.list() == [record]


def test_memory_store_search_is_case_insensitive_and_scoped(tmp_path):
    store = MemoryStore(tmp_path / "memory.jsonl")
    store.add({"content": "Project uses Pytest", "scope": "project"})
    store.add({"content": "User likes concise answers", "scope": "user"})

    assert [item["content"] for item in store.search("pytest")] == ["Project uses Pytest"]
    assert store.search("project", scope="user") == []


def test_memory_store_missing_file_returns_empty_lists(tmp_path):
    store = MemoryStore(tmp_path / "missing.jsonl")

    assert store.list() == []
    assert store.search("anything") == []


def test_memory_tools_remember_and_search(tmp_path):
    store = MemoryStore(tmp_path / "memory.jsonl")
    provider = MemoryToolProvider(store)
    tools_by_name = {tool.name: tool for tool in provider.load_tools()}

    output = tools_by_name["remember"].handler({"content": "Prefer tests first"})

    assert output == "OK: remembered Prefer tests first"
    assert "Prefer tests first" in tools_by_name["memory_search"].handler({"query": "tests"})
    assert tools_by_name["remember"].requires_approval is True
