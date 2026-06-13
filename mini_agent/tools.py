import subprocess
from pathlib import Path

"""
read_file({"path": "foo.txt", "start": 0})
write_file({"path": "bar.txt", "content": "hello"})
search_files({"query": "hello", "root": ".", "glob": "**/*.py"})
exec_command({"command": "python --version", "cwd": ".", "timeout": 30})

WARNING: tools that execute code or access the filesystem can be dangerous. Always review tool definitions and handlers carefully before use.
"""


READ_BUFFER_SIZE = 4000
MAX_TOOL_OUTPUT = 4000
TEXT_ENCODINGS = ("utf-8-sig", "gb18030")


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
    "description": "Read a text range from a file. Use start/end to continue reading long files.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read."},
            "start": {
                "type": "integer",
                "description": "Zero-based character offset to start reading from. Defaults to 0.",
            },
            "end": {
                "type": "integer",
                "description": "Zero-based character offset to stop before. Defaults to start + buffer size.",
            },
        },
        "required": ["path"],
    },
}

WRITE_FILE_TOOL = {
    "type": "function",
    "name": "write_file",
    "description": "Write text content to a file. Creates parent directories when needed.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to write."},
            "content": {"type": "string", "description": "Text content to write."},
        },
        "required": ["path", "content"],
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
    },
}


def read_file(args):
    try:
        content = read_text(args["path"])
        total = len(content)
        start = max(0, int(args.get("start") or 0))
        end = args.get("end")
        if end is None:
            end = start + READ_BUFFER_SIZE
        end = min(total, max(start, int(end)))
        next_start = end if end < total else None
        header = f"range: {start}-{end} / {total}\nnext_start: {next_start}\n\n"
        return header + content[start:end]
    except Exception as e:
        return f"ERROR: {e}"  # Return errors as text so the model can handle them


def write_file(args):
    try:
        path = Path(args["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        return f"OK: wrote {len(args['content'])} chars to {path}"
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
    (READ_FILE_TOOL, read_file),
    (WRITE_FILE_TOOL, write_file),
    (SEARCH_FILES_TOOL, search_files),
    (EXEC_COMMAND_TOOL, exec_command),
]
