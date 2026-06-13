# Mini Agent

This is the smallest runnable Agent example in the `DIY Your AI Agent` repository. It uses plain Python and the OpenAI Responses API to demonstrate a basic ReAct + tool-calling loop.

## Quick Start

From the repository root, install the dependencies and create your environment file:

```shell
pip install -r requirements.txt
cp mini_agent/.env.example .env
```

Edit the root `.env` file with your API key, base URL, and model name:

```plaintext
API_KEY=your_api_key_here
BASE_URL=https://api.openai.com/v1
MODEL=your_model_name
```

Run the agent from the repository root:

```shell
python .\mini_agent\agent.py
```

Use `/exit` or `/quit` to stop the program.

## Interactive Commands

- `/exit`: stop the program.
- `/quit`: stop the program.
- `/bypass`: toggle approval bypass mode. When enabled, `exec_command` and `write_file` run without asking for confirmation. Run it again to turn bypass off.

## Current Capabilities

- Asks for user approval before running `exec_command` or `write_file` by default.
- Includes four local tools:
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
                 ├─ ask user to approve or reject
                 └─ handler(args)
```

## File Layout

```text
mini_agent/
├── agent.py        # Agent loop: model calls, tool dispatch, terminal interaction
├── tools.py        # Tool schemas and execution handlers
└── .env.example    # Environment variable example
```

## Reading Guide

Start with `agent.py`:

1. `SYSTEM_PROMPT`: defines the Agent's core behavior constraints.
2. `Agent.run()`: runs one user task and loops over model outputs and tool calls.
3. `run_tool_calls()`: turns model function calls into local tool executions.
4. `register_tool()`: binds each tool schema to its Python handler.

Then move to `tools.py`:

1. Each tool has a JSON schema that tells the model how to call it.
2. Each tool has a Python function that performs the work.
3. `BUILTIN_TOOLS` pairs schemas with handlers and passes them to the Agent for registration.

## Safety Note

This example can read files, write files, and execute shell commands. Avoid running it casually in directories that contain sensitive files, and never commit your real `.env` to GitHub.
