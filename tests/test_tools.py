import sys

from mini_agent import tools


def python_command(code):
    return f'"{sys.executable}" -c "{code}"'


def test_truncate_keeps_short_text():
    assert tools.truncate("abc", limit=3) == "abc"


def test_truncate_marks_long_text():
    assert tools.truncate("abcdef", limit=3) == "abc\n... truncated to 3 chars"


def test_read_text_handles_utf8_sig(tmp_path):
    path = tmp_path / "utf8_sig.txt"
    path.write_bytes(b"\xef\xbb\xbfhello")

    assert tools.read_text(path) == "hello"


def test_read_text_falls_back_to_gb18030(tmp_path):
    path = tmp_path / "gb18030.txt"
    path.write_bytes(b"\xc4\xe3\xba\xc3")

    assert tools.read_text(path) == "\u4f60\u597d"


def test_read_file_returns_default_range_header(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("hello", encoding="utf-8")

    output = tools.read_file({"path": str(path)})

    assert output == "range: 0-5 / 5\nnext_start: None\n\nhello"


def test_read_file_applies_start_end_bounds(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("abcdef", encoding="utf-8")

    output = tools.read_file({"path": str(path), "start": -3, "end": 3})

    assert output == "range: 0-3 / 6\nnext_start: 3\n\nabc"


def test_read_file_returns_error_for_missing_file(tmp_path):
    output = tools.read_file({"path": str(tmp_path / "missing.txt")})

    assert output.startswith("ERROR:")


def test_write_file_creates_parent_dirs_and_writes_utf8(tmp_path):
    path = tmp_path / "nested" / "file.txt"

    output = tools.write_file({"path": str(path), "content": "hello \u2603"})

    assert output.startswith("OK: wrote 7 chars to ")
    assert path.read_text(encoding="utf-8") == "hello \u2603"


def test_search_files_is_case_insensitive_and_respects_glob(tmp_path):
    py_file = tmp_path / "a.py"
    txt_file = tmp_path / "b.txt"
    py_file.write_text("Alpha HELLO\n", encoding="utf-8")
    txt_file.write_text("hello but ignored\n", encoding="utf-8")

    output = tools.search_files(
        {"query": "hello", "root": str(tmp_path), "glob": "*.py"}
    )

    assert "Alpha HELLO" in output
    assert "ignored" not in output


def test_search_files_returns_no_matches(tmp_path):
    path = tmp_path / "a.py"
    path.write_text("print('nothing')\n", encoding="utf-8")

    output = tools.search_files({"query": "hello", "root": str(tmp_path)})

    assert output == "No matches found"


def test_exec_command_returns_exit_code_stdout_and_stderr(tmp_path):
    output = tools.exec_command(
        {
            "command": python_command("import sys; print('out'); print('err', file=sys.stderr)"),
            "cwd": str(tmp_path),
        }
    )

    assert "exit_code: 0" in output
    assert "stdout:\nout" in output
    assert "stderr:\nerr" in output


def test_exec_command_reports_timeout():
    output = tools.exec_command(
        {"command": python_command("import time; time.sleep(2)"), "timeout": 1}
    )

    assert output == "ERROR: command timed out after 1 seconds"


def test_builtin_tools_have_matching_schema_and_handlers():
    names = [definition["name"] for definition, _ in tools.BUILTIN_TOOLS]

    assert names == ["read_file", "write_file", "search_files", "exec_command"]
    for definition, handler in tools.BUILTIN_TOOLS:
        assert definition["type"] == "function"
        assert definition["name"] == handler.__name__
        assert definition["parameters"]["type"] == "object"
        assert "required" in definition["parameters"]
