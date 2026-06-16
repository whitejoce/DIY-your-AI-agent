import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

"""
read_file({"path": "foo.txt", "start_line": 1})
edit_file({"path": "foo.txt", "start_line": 1, "end_line": 1, "replacement": "hello"})
search_files({"query": "hello", "root": ".", "glob": "**/*.py"})
exec_command({"command": "python --version", "cwd": ".", "timeout": 30})

WARNING: tools that execute code or access the filesystem can be dangerous. Always review tool definitions and handlers carefully before use.
"""


READ_BUFFER_LINES = 120
MAX_TOOL_OUTPUT = 4000
TEXT_ENCODINGS = ("utf-8-sig", "gb18030")


@dataclass(frozen=True)
class ToolSpec:
    definition: dict
    handler: Callable[[dict], str]
    requires_approval: bool = False


def truncate(text, limit=MAX_TOOL_OUTPUT):
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... truncated to {limit} chars"


def read_text(path):
    data = Path(path).read_bytes()
    for encoding in TEXT_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


# Harness layer: tool definitions and execution
# doc: https://developers.openai.com/api/docs/guides/function-calling
READ_FILE_TOOL = {
    "type": "function",
    "name": "read_file",
    "description": "Read numbered lines from a text file. Use start_line/end_line to continue reading long files.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read."},
            "start_line": {
                "type": "integer",
                "description": "1-based line number to start reading from. Defaults to 1.",
            },
            "end_line": {
                "type": "integer",
                "description": "1-based line number to stop at, inclusive. Defaults to start_line + 119.",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}

EDIT_FILE_TOOL = {
    "type": "function",
    "name": "edit_file",
    "description": "Replace a 1-based inclusive line range in a text file. Read the file first, then edit only the needed lines.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to edit."},
            "start_line": {
                "type": "integer",
                "description": "1-based first line to replace.",
            },
            "end_line": {
                "type": "integer",
                "description": "1-based last line to replace, inclusive.",
            },
            "replacement": {
                "type": "string",
                "description": "Replacement text for the selected line range. Other file lines are preserved.",
            },
        },
        "required": ["path", "start_line", "end_line", "replacement"],
        "additionalProperties": False,
    },
}

SEARCH_FILES_TOOL = {
    "type": "function",
    "name": "search_files",
    "description": "Search for text in files under a directory.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text to search for."},
            "root": {
                "type": "string",
                "description": "Directory to search from. Defaults to current directory.",
            },
            "glob": {
                "type": "string",
                "description": "File glob pattern. Defaults to **/*.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}

EXEC_COMMAND_TOOL = {
    "type": "function",
    "name": "exec_command",
    "description": "Execute a shell command and return stdout, stderr, and exit code.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command to execute."},
            "cwd": {
                "type": "string",
                "description": "Working directory. Defaults to current directory.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds. Defaults to 30.",
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    },
}


def read_file(args):
    try:
        content = read_text(args["path"])
        lines = content.splitlines()
        total = len(lines)
        start_line = max(1, int(args.get("start_line") or 1))
        end_line = args.get("end_line")
        if end_line is None:
            end_line = start_line + READ_BUFFER_LINES - 1
        end_line = max(start_line, int(end_line))
        if total:
            end_line = min(total, end_line)
        else:
            end_line = 0
        next_start_line = end_line + 1 if end_line < total else None
        selected_lines = lines[start_line - 1 : end_line]
        numbered = "\n".join(
            f"{line_number}: {line}"
            for line_number, line in enumerate(selected_lines, start=start_line)
        )
        header = (
            f"lines: {start_line}-{end_line} / {total}\n"
            f"next_start_line: {next_start_line}\n\n"
        )
        return truncate(header + numbered)
    except Exception as e:
        return f"ERROR: {e}"  # Return errors as text so the model can handle them


def detect_newline(text):
    if "\r\n" in text:
        return "\r\n"
    if "\n" in text:
        return "\n"
    if "\r" in text:
        return "\r"
    return "\n"


def replacement_to_lines(replacement, newline, keep_final_newline=True):
    if replacement == "":
        return []
    normalized = replacement.replace("\r\n", "\n").replace("\r", "\n")
    parts = normalized.split("\n")
    ends_with_newline = parts[-1] == ""
    if ends_with_newline:
        parts = parts[:-1]

    lines = [part + newline for part in parts]
    if lines and not ends_with_newline and not keep_final_newline:
        lines[-1] = lines[-1][: -len(newline)]
    return lines


def edit_file(args):
    try:
        path = Path(args["path"])
        start_line = int(args["start_line"])
        end_line = int(args["end_line"])
        replacement = args["replacement"]

        if start_line < 1 or end_line < start_line:
            return "ERROR: line range must use 1-based start_line <= end_line"

        if not path.exists():
            if start_line != 1 or end_line != 1:
                return "ERROR: file does not exist; create it with start_line=1 and end_line=1"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(replacement, encoding="utf-8", newline="")
            return f"OK: created {path} with {len(replacement.splitlines())} lines"

        content = read_text(path)
        lines = content.splitlines(keepends=True)
        total = len(lines)
        if total == 0:
            if start_line != 1 or end_line != 1:
                return "ERROR: empty file can only be edited with start_line=1 and end_line=1"
        elif end_line > total:
            return f"ERROR: line range {start_line}-{end_line} exceeds file length {total}"

        newline = detect_newline(content)
        keep_final_newline = end_line < total or content.endswith(("\n", "\r"))
        new_lines = replacement_to_lines(
            replacement,
            newline,
            keep_final_newline=keep_final_newline,
        )
        lines[start_line - 1 : end_line] = new_lines
        path.write_text("".join(lines), encoding="utf-8", newline="")
        return f"OK: replaced lines {start_line}-{end_line} in {path}"
    except Exception as e:
        return f"ERROR: {e}"


def search_files(args):
    try:
        query = args["query"]
        root = Path(args.get("root") or ".")
        glob_pattern = args.get("glob") or "**/*"
        matches = []

        for path in root.glob(glob_pattern):
            if not path.is_file():
                continue
            try:
                for line_number, line in enumerate(
                    read_text(path).splitlines(), start=1
                ):
                    if query.lower() in line.lower():
                        matches.append(f"{path}:{line_number}: {line}")
                        if len(matches) >= 50:
                            return truncate("\n".join(matches))
            except Exception:
                continue

        return truncate("\n".join(matches)) if matches else "No matches found"
    except Exception as e:
        return f"ERROR: {e}"


def exec_command(args):
    try:
        timeout = int(args.get("timeout") or 30)
        completed = subprocess.run(
            args["command"],
            cwd=args.get("cwd") or None,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = (
            f"exit_code: {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
        return truncate(output)
    except subprocess.TimeoutExpired as e:
        return f"ERROR: command timed out after {e.timeout} seconds"
    except Exception as e:
        return f"ERROR: {e}"


BUILTIN_TOOLS = [
    ToolSpec(READ_FILE_TOOL, read_file),
    ToolSpec(EDIT_FILE_TOOL, edit_file, requires_approval=True),
    ToolSpec(SEARCH_FILES_TOOL, search_files),
    ToolSpec(EXEC_COMMAND_TOOL, exec_command, requires_approval=True),
]
