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


def test_read_file_returns_default_numbered_lines(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("hello\nworld\n", encoding="utf-8")

    output = tools.read_file({"path": str(path)})

    assert output == "lines: 1-2 / 2\nnext_start_line: None\n\n1: hello\n2: world"


def test_read_file_applies_line_bounds(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("a\nb\nc\n", encoding="utf-8")

    output = tools.read_file({"path": str(path), "start_line": 2, "end_line": 2})

    assert output == "lines: 2-2 / 3\nnext_start_line: 3\n\n2: b"


def test_read_file_returns_error_for_missing_file(tmp_path):
    output = tools.read_file({"path": str(tmp_path / "missing.txt")})

    assert output.startswith("ERROR:")


def test_edit_file_replaces_single_line_and_preserves_rest(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("old first\nsecond\nthird\n", encoding="utf-8")

    output = tools.edit_file(
        {
            "path": str(path),
            "start_line": 1,
            "end_line": 1,
            "replacement": "new first",
        }
    )

    assert output == f"OK: replaced lines 1-1 in {path}"
    assert path.read_text(encoding="utf-8") == "new first\nsecond\nthird\n"


def test_edit_file_replaces_multiple_lines(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")

    output = tools.edit_file(
        {
            "path": str(path),
            "start_line": 2,
            "end_line": 3,
            "replacement": "TWO\nTHREE",
        }
    )

    assert output == f"OK: replaced lines 2-3 in {path}"
    assert path.read_text(encoding="utf-8") == "one\nTWO\nTHREE\nfour\n"


def test_edit_file_creates_missing_file(tmp_path):
    path = tmp_path / "nested" / "file.txt"

    output = tools.edit_file(
        {
            "path": str(path),
            "start_line": 1,
            "end_line": 1,
            "replacement": "hello \u2603",
        }
    )

    assert output == f"OK: created {path} with 1 lines"
    assert path.read_text(encoding="utf-8") == "hello \u2603"


def test_edit_file_rejects_out_of_range_lines(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("one\n", encoding="utf-8")

    output = tools.edit_file(
        {
            "path": str(path),
            "start_line": 2,
            "end_line": 2,
            "replacement": "two",
        }
    )

    assert output == "ERROR: line range 2-2 exceeds file length 1"


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
    names = [spec.definition["name"] for spec in tools.BUILTIN_TOOLS]

    assert names == ["read_file", "edit_file", "search_files", "exec_command"]
    for spec in tools.BUILTIN_TOOLS:
        assert isinstance(spec, tools.ToolSpec)
        definition = spec.definition
        handler = spec.handler
        assert definition["type"] == "function"
        assert definition["name"] == handler.__name__
        assert definition["parameters"]["type"] == "object"
        assert "required" in definition["parameters"]
        assert definition["parameters"]["additionalProperties"] is False

    approval_by_name = {
        spec.definition["name"]: spec.requires_approval for spec in tools.BUILTIN_TOOLS
    }
    assert approval_by_name == {
        "read_file": False,
        "edit_file": True,
        "search_files": False,
        "exec_command": True,
    }
