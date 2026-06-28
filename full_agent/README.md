# Full Agent

`full_agent` is the extensible Agent runtime in the `DIY Your AI Agent` repository.
It keeps the readability of `mini_agent`, but splits the runtime into clearer
modules so it can grow toward long-term memory, skills, MCP, RAG, and external
tool ecosystems.

The core design principle is:

> Build the Agent harness ourselves, and connect external capabilities through adapters.

This means the project owns the control layer: loop, context, tool dispatch,
approval, safety policy, and tests. Mature external systems such as LangChain,
MCP SDKs, vector stores, and data connectors should be wrapped as `ToolProvider`
implementations instead of being baked into the runtime.

## Features

- `AgentRuntime`: ReAct loop, model calls, tool calls, short-term context, and max-turn protection.
- `ModelClient` adapters: OpenAI Responses API, OpenAI Chat Completions API, and an Anthropic Messages API entry point.
- `ToolRegistry` / `ToolExecutor`: unified tool registration and execution with globally unique tool names.
- `ApprovalPolicy`: confirmation before high-risk tools such as `edit_file`, `exec_command`, and `remember`.
- `ConversationMemory` / `ContextManager`: current-session history and character-budget trimming.
- `MemoryStore`: long-term memory stored in `.agent/memory.jsonl`.
- `SkillLoader`: directory-based instruction skills without dynamic Python execution.
- `StaticMCPToolProvider`: MCP provider interface plus a test double, without connecting to a real MCP server yet.
- CLI: interactive terminal entry via `python -m full_agent`.

## Quick Start

Install dependencies from the repository root:

```shell
pip install -r requirements.txt
```

Create or edit `full_agent/.env`:

```plaintext
MODEL_PROVIDER=openai
MODEL_API=responses
API_KEY=your_api_key_here
BASE_URL=https://api.openai.com/v1
MODEL=your_model_name
MAX_TOKENS=2048
TEMPERATURE=0.2
```

Run the agent:

```shell
python -m full_agent
```

Available CLI commands:

```text
/exit      Exit
/quit      Exit
/bypass    Toggle approval bypass for dangerous tools
/tools     List registered tools
/skills    List discovered skills
/memory    Show long-term memory
```

`AgentConfig.from_env()` loads `full_agent/.env` by default, so running
`python -m full_agent` from another directory will not accidentally load a
different `.env`. Existing system environment variables take priority over
values in the `.env` file.

## Model API Selection

Switch model backends with `MODEL_PROVIDER` and `MODEL_API`:

```plaintext
MODEL_PROVIDER=openai
MODEL_API=responses

MODEL_PROVIDER=openai
MODEL_API=chat_completions

MODEL_PROVIDER=anthropic
MODEL_API=anthropic_messages
```

The Anthropic path requires installing the `anthropic` package separately.

## Architecture Boundary

`full_agent` does not use LangChain or LangGraph as the main runtime. The goal is
to learn and control the key mechanics of an Agent harness instead of handing the
main control flow to an external framework.

```text
full_agent owns
  - AgentRuntime
  - tool-calling loop
  - context management
  - memory policy
  - approval policy
  - CLI and tests

external frameworks provide
  - RAG loaders, splitters, retrievers, and vector stores
  - MCP client/server connections
  - third-party data connectors
  - specialized tool implementations

adapter layer connects them
  - LangChainRAGToolProvider
  - MCPToolProvider
  - other ToolProvider implementations
```

## Project Layout

```text
full_agent/
├──  __main__.py          # python -m full_agent entry point
├──  cli.py               # interactive terminal
├──  config.py            # AgentConfig / ModelConfig
├──  runtime.py           # AgentRuntime main loop
├──  model.py             # ModelClient abstraction and provider adapters
├──  context.py           # short-term conversation and context trimming
├──  memory.py            # JSONL long-term memory
├──  skills.py            # directory-based skill loading
├──  mcp.py               # MCP provider protocol and static test provider
├──  approval.py          # tool approval policy
└──  tools/
    ├──  base.py          # ToolSpec / ToolRegistry / ToolExecutor
    ├──  builtin.py       # mini_agent built-in tool adapters
    └──  memory_tools.py  # remember / memory_search
```

## Extending Tools

External capabilities should be wrapped as a `ToolProvider` and registered into
the `ToolRegistry`:

```python
class ToolProvider:
    def load_tools(self):
        ...
```

Each tool is described with `ToolSpec`:

```python
ToolSpec(
    definition={...},          # OpenAI function schema
    handler=callable,          # Python handler
    source="rag:langchain",    # tool source
    requires_approval=False,   # whether approval is required
)
```

This keeps the runtime independent from whether a tool comes from a local Python
function, a LangChain retriever, an MCP server, or another external service.

## RAG and MCP

RAG should be added through an adapter instead of being implemented directly in
the runtime:

```text
LangChain retriever
  -> LangChainRAGToolProvider
  -> ToolSpec(name="rag_search")
  -> AgentRuntime
```

MCP should follow the same pattern:

```text
MCP server
  -> MCP client / LangChain MCP adapter
  -> MCPToolProvider
  -> ToolSpec
  -> AgentRuntime
```

Once tools enter the runtime, they should follow the same rules: unique names,
approval for high-risk actions, readable error output, and output truncation to
protect the context window.

## Skills

`SkillLoader` reads directory-based skills under `.agent/skills/`:

```text
.agent/skills/example-skill/
├──  skill.json
└──  SKILL.md
```

Example `skill.json`:

```json
{
  "name": "pytest-helper",
  "description": "Help with Python test workflows.",
  "triggers": ["pytest", "test failure"],
  "instructions": "SKILL.md"
}
```

When a user task matches the skill name or triggers, the runtime loads the
corresponding `SKILL.md` and injects it as relevant instructions. It does not
dynamically import or execute Python code from skill directories.

## Long-Term Memory

Long-term memory is stored at:

```text
.agent/memory.jsonl
```

Built-in memory tools:

- `remember`: save a long-term memory, with approval required by default.
- `memory_search`: case-insensitive keyword search over memory entries.

`.agent/` is ignored by Git to avoid committing local memory.

## Roadmap

- `LangChainRAGToolProvider`
- `LangChainMCPToolProvider`
- Official MCP SDK provider
- Better logging and traces
- Stronger context compression
