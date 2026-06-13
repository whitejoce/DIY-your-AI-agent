# Mini Agent

This is the minimal runnable Agent example in the `DIY Your AI Agent` repository. It directly uses Python and the OpenAI Responses API to demonstrate the basic ReAct + Tool Calling loop.

## Quick Start

Install dependencies and prepare the environment from the repository root:

```shell
pip install -r requirements.txt
cp mini_agent/.env.example .env
```

Edit the root `.env` file and fill in your API key, base URL, and model name:

```plaintext
API_KEY=your_api_key_here
BASE_URL=https://api.openai.com/v1
MODEL=your_model_name
```

Run from the repository root:

```shell
python .\mini_agent\agent.py
```

Type `/exit` or `/quit` to exit.

## Interactive Commands

- `/exit`: exit the program.
- `/quit`: exit the program.
- `/bypass`: toggle approval bypass mode. When enabled, `exec_command` and `write_file` no longer ask for confirmation. Enter it again to turn bypass off.

## Current Capabilities

- Requests user approval by default before running `exec_command` or `write_file`.
- Includes 4 local tools:
  - `read_file`: read text files.
  - `write_file`: write text files.
  - `search_files`: search file contents.
  - `exec_command`: execute shell commands.

```markdown
main loop
  ├─ handle user commands: /exit /quit /bypass
  └─ agent.run(task)
       └─ run_tool_calls()
            └─ run_tool()
                 ├─ approval_policy.should_approve(name, args)
                 ├─ ask user to approve / reject
                 └─ handler(args)
```

## File Guide

```text
mini_agent/
├── agent.py        # Agent loop: model calls, tool dispatch, terminal interaction
├── tools.py        # Tool schemas and execution handlers
└── .env.example    # Environment variable example
```

## How to Read the Code

Start with `agent.py`:

1. `SYSTEM_PROMPT`: defines the Agent's basic behavior constraints.
2. `Agent.run()`: executes one user task and loops through model outputs and tool calls.
3. `run_tool_calls()`: converts model function calls into real tool executions.
4. `register_tool()`: binds a tool schema to its Python handler.

Then read `tools.py`:

1. Each tool has a JSON schema that tells the model how to call it.
2. Each tool has a Python function that performs the actual execution.
3. `BUILTIN_TOOLS` combines schemas and handlers, then passes them to the Agent for registration.

## Safety Note

This example can read and write files and execute shell commands. Do not test it casually in directories that contain sensitive files, and do not commit your real `.env` to GitHub.
