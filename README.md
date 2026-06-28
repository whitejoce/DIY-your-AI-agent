# DIY Your AI Agent

<p align="center">
   <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-blue">
   <img alt="OpenAI SDK" src="https://img.shields.io/badge/OpenAI%20SDK-1.35%2B-111827">
   <img alt="License" src="https://img.shields.io/badge/License-MIT-green">
   <a href="https://deepwiki.com/whitejoce/DIY-your-AI-agent"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
</p>
<p align="center">
  <a href="./README_CN.md">中文文档</a>
</p>

**This project is part of the [whitejoce/AI-Agent-Toolkit](https://github.com/whitejoce) stack, focusing on the Agent layer.**  
Full architecture: [RAG (Enterprise Knowledge Base)](https://github.com/whitejoce/RAG-Demo) → [Agent](https://github.com/whitejoce/DIY-your-AI-agent) → [Tool Runtime (Hot-reloadable MCP Tools Platform)](https://github.com/whitejoce/ToolFlow)

---

## 🔥 Project Overview
> Translated by GPT-5.5

A lightweight AI Agent runtime built from scratch for learning and understanding:
* How an LLM enters a tool-calling loop
* How to build from basic tool dispatch without using LangChain / LangGraph as the main runtime framework, then gradually expand into context, memory, approval, Skills, and MCP modules.

<p align="center">
   <img src="./img/demo.png" alt="DIY Your AI Agent demo" width="900" style="border:1px solid #ccc; border-radius:8px;">
</p>

### Mini Agent

The MVP example in this repository lives in [`mini_agent/`](./mini_agent/), and the extensible runtime lives in [`full_agent/`](./full_agent/).

- Usage guide: [mini_agent/README.md](./mini_agent/README.md)
- Entry point: `mini_agent/agent.py`
- Tool definitions: `mini_agent/tools.py`

### Full Agent

A complete Agent runtime with multiple model providers, tool registration, approval policy, context management, long-term memory, and Skill loading.

- Full Agent guide: [full_agent/README.md](./full_agent/README.md)
- Entry point: `full_agent/cli.py`

## Project Structure

```text
.
├── requirements.txt        # Runtime Python dependencies
├── requirements-dev.txt    # Development and test dependencies
├── pytest.ini              # Pytest configuration
├── mini_agent/
│   ├── agent.py        # Agent loop: model calls, tool dispatch, terminal interaction
│   ├── tools.py        # Tool schemas and execution handlers
│   ├── README_*.md     # Documentation
│   └── .env.example    # Environment variable example
├── full_agent/
│   ├── runtime.py      # Extensible AgentRuntime main loop
│   ├── model.py        # Model provider adapters
│   ├── config.py       # Configuration loading
│   ├── memory.py       # JSONL long-term memory
│   ├── skills.py       # Directory-based instruction skill loading
│   ├── mcp.py          # MCP provider protocol and test double
│   ├── tools/          # ToolSpec / ToolRegistry / ToolExecutor
│   └── README_*.md     # Documentation
├── tests/              # Automated tests for mini_agent and full_agent
├── img/demo.png        # Demo screenshot
├── README_CN.md        # Chinese README
├── README.md           # English README
└── LICENSE
```

## Roadmap

Keep `Mini Agent` as the learning and testing base. `Full Agent` already includes:

- `ToolRegistry`: manage built-in tools, third-party tools, and MCP tools in one place.
- `ApprovalPolicy`: ask for user confirmation before high-risk actions such as writing files or running commands.
- `ContextManager`: manage short-term context, conversation compression, and token budgets.
- `Memory`: store long-term memory, user preferences, and project-level context.

Next steps can add RAG adapters, a real MCP SDK provider, better logging and traces, and stronger context compression.

## Testing

Install the development dependencies and run the test suite from the repository root:

```shell
pip install -r requirements-dev.txt
python -m pytest
```

The tests cover tool handlers, configuration, memory, Skills, the MCP provider interface, and Agent tool dispatch for both `mini_agent` and `full_agent` without calling the OpenAI API.

## Safety Note

> This repository is better suited for learning the basic structure and extension boundaries of an Agent runtime. For production use, combine it with mature community projects and a more complete safety policy.

---

## 💡 Further Reading

### 1. Talk to a Frontier Model
- LLM
   - OpenAI: [model-spec.md](https://model-spec.openai.com/)
   - Anthropic: [System Card](https://www.anthropic.com/system-cards) and [System Prompt](https://platform.claude.com/docs/en/release-notes/system-prompts)
      - knowledge_cutoff

- LLM APIs
   - OpenAI: [Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses#about-the-responses-api) and `Chat Completions API`
   - Anthropic: [Messages API](https://platform.claude.com/docs/en/build-with-claude/working-with-messages)
- [MCP](https://modelcontextprotocol.io/introduction), [Skills](https://agentskills.io/specification): progressive disclosure
   - ~~Prompt engineering~~, Context Engineering vs Harness Engineering -> Loop Engineering
      - Why are prompts becoming less important?
         - Human-in-the-loop?
- Agentic AI
   - Function calling, [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), Hooks
   - Observability and orchestration: logs, tool-call traces, error tracking, and performance monitoring
- Benchmarks and evaluation
   - [Artificial Analysis](https://artificialanalysis.ai/models) and [Deep SWE benchmark](https://deepswe.datacurve.ai/)
- Multi-agent frameworks and SDKs
   - ADK: `A2A protocol` and `agent.json`
   - Design patterns behind frameworks such as LangGraph and LangChain
- LLM output quality
   - Correctness, Completeness, Size, Trjectory: [No Vibes Allowed: Solving Hard Problems in Complex Codebases – Dex Horthy, HumanLayer](https://www.youtube.com/watch?v=rmvDxxNubIg)

> Looking for an Agent SDK?
> Check out [DeepAgent](https://docs.langchain.com/oss/python/deepagents/overview), [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/quickstart).

### 2. Context Management Trade-offs

Recommended: [Claude Code's animated context-window demo](https://code.claude.com/docs/en/context-window).

- Short-term memory: select and preserve the most relevant information in the current conversation
   - What is the `dumb zone`?
   - Context compression: summarize earlier turns to save tokens while preserving continuity
- Long-term memory: retain user preferences, conversation history, and project context for better continuity
   - `AGENT.md` and `CLAUDE.md`: global and project-level context files
   - Memory systems: persist command history, user preferences, and related project facts
- External knowledge bases: Retrieval-Augmented Generation (RAG)

### 3. Explore Harness Design

> What is a harness, and why does it matter in agent design?

- [OpenClaw](https://github.com/openclaw/openclaw), [Hermes Agent](https://github.com/nousresearch/hermes-agent), [OpenHuman](https://github.com/tinyhumansai/openhuman), [Pi](https://pi.dev/)
- **Coding agents**: [Cursor](https://www.cursor.com/), [Codex](https://openai.com/codex), [Claude Code](https://code.claude.com/docs), [OpenCode](https://opencode.ai/)
   - Deep dive: understand how [Pi](https://github.com/earendil-works/pi) works

---

## 📜 License

This project is released under the **MIT License**. 

## 🤝 Contributions

Issues and PRs are welcome. 
