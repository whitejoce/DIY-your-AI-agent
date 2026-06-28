# DIY Your AI Agent

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-blue">
  <img alt="OpenAI SDK" src="https://img.shields.io/badge/OpenAI%20SDK-1.35%2B-111827">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green">
  <a href="https://deepwiki.com/whitejoce/DIY-your-AI-agent"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
</p>


**本项目是 [whitejoce/AI-Agent-Toolkit](https://github.com/whitejoce) 技术栈的一部分，专注于 Agent 层。**  
完整技术路线：[RAG](https://github.com/whitejoce/RAG-Demo)（企业知识库） → [Agent](https://github.com/whitejoce/DIY-your-AI-agent) → [Tool Runtime](https://github.com/whitejoce/ToolFlow)（可热加载的MCP Tools平台）

---

## 🔥 项目简介  

这是一个从 0 实现的轻量 AI Agent runtime，用于学习和理解：
* LLM 如何进入 tool calling loop
* 不依赖 LangChain / LangGraph 等主 runtime 框架，从最基础的工具调度逻辑开始构建，并逐步扩展到上下文、记忆、审批、Skill 和 MCP 等模块。

<p align="center">
  <img src="./img/demo.png" alt="DIY Your AI Agent demo" width="900" style="border:1px solid #ccc; border-radius:8px;">
</p>

### Mini Agent

当前仓库里的 MVP 示例放在 [`mini_agent/`](./mini_agent/) 目录下，可扩展版 runtime 放在 [`full_agent/`](./full_agent/) 目录下。

- 使用说明：[mini_agent/README_CN.md](./mini_agent/README_CN.md)
- 入口文件：`mini_agent/agent.py`
- 工具定义：`mini_agent/tools.py`

### Full Agent

完整的Agent runtime，支持多种模型供应商、工具注册、审批策略、上下文管理、长期记忆和 Skill 加载。

- Full Agent 使用说明：[full_agent/README_CN.md](./full_agent/README_CN.md)
- 入口文件：`full_agent/cli.py`

## 代码结构

```text
.
├── requirements.txt        # 运行时 Python 依赖
├── requirements-dev.txt    # 开发和测试依赖
├── pytest.ini              # Pytest 配置
├── mini_agent/
│   ├── agent.py        # Agent 主循环：模型调用、工具调度、终端交互
│   ├── tools.py        # 工具定义和工具执行函数
│   ├── README_*.md     # 说明文档
│   └── .env.example    # 环境变量示例
├── full_agent/
│   ├── runtime.py      # 可扩展 AgentRuntime 主循环
│   ├── model.py        # 模型供应商 adapter
│   ├── config.py       # 配置加载
│   ├── memory.py       # JSONL 长期记忆
│   ├── skills.py       # 目录型 instruction skill 加载
│   ├── mcp.py          # MCP provider 协议和测试替身
│   ├── tools/          # ToolSpec / ToolRegistry / ToolExecutor
│   └── README_*.md     # 说明文档
├── tests/              # mini_agent 和 full_agent 自动化测试
├── img/demo.png        # 运行截图
├── README_CN.md        # 中文说明
├── README.md           # 英文说明
└── LICENSE
```

## 正式版路线图

保留 `Mini Agent` 作为学习和测试的基础，`Full Agent` 已经加入以下模块：

- `ToolRegistry`：统一管理内置工具、第三方工具和 MCP 工具。
- `ApprovalPolicy`：在执行写文件、执行命令等高风险工具前请求用户确认。
- `ContextManager`：负责短期上下文、长对话压缩和 token 预算。
- `Memory`：保存长期记忆、用户偏好和项目级上下文。

下一步可以继续补充 RAG adapter、真实 MCP SDK provider、更完整的日志和 trace，以及更强的上下文压缩策略。

## 测试

在仓库根目录安装开发依赖并运行测试：

```shell
pip install -r requirements-dev.txt
python -m pytest
```

测试会覆盖 `mini_agent` 和 `full_agent` 的工具处理函数、配置、记忆、Skill、MCP provider 接口和 Agent 工具调度逻辑，不会调用 OpenAI API。

## 安全提示

> 这个仓库更适合学习 Agent runtime 的基本结构和扩展边界。日常生产使用时，建议结合成熟社区项目和更完整的安全策略。



---

## 💡 See Also

### 1. 与SOTA模型交流

- LLM
   - OpenAI: [model-spec.md](https://model-spec.openai.com/)
   - Anthropic: [System Card](https://www.anthropic.com/system-cards) and [System Prompt](https://platform.claude.com/docs/en/release-notes/system-prompts)

- LLM API
  - OpenAI：[Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses#about-the-responses-api)、`Chat Completions API`
  - Anthropic：[Messages API](https://platform.claude.com/docs/zh-CN/build-with-claude/working-with-messages)
- [MCP 协议](https://modelcontextprotocol.io/introduction)、[Skills](https://agentskills.io/specification) :渐进式披露
- ~~提示词工程~~,上下文工程 vs Harness 工程 -> [Loop Engineering](https://www.runoob.com/ai-agent/loop-engineering.html)
  - 为什么提示词变得没那么重要了？
    - Human-in-the-loop?
- Agentic AI
  - Function Calling、[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)、Hooks
  - 可观测性与编排：日志、工具调用记录、错误追踪、性能监控
- 评分与评测
  - [Artificial Analysis](https://artificialanalysis.ai/models)、[Deep SWE benchmark](https://deepswe.datacurve.ai/)

> 在寻找Agent SDK？
> 可以看看 [DeepAgent](https://docs.langchain.com/oss/python/deepagents/overview)、[OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/quickstart)

- Multi-Agent: Agent SDK
  - ADK：`A2A 协议`、`agent.json`
  - LangGraph、LangChain 等框架的设计理念和实现细节
- 衡量 LLM 输出的质量
  - 准确性、完整性、长度、路径: [利用 Harness Engineering 解决复杂问题 – Dex Horthy, HumanLayer](https://www.bilibili.com/video/BV1EyQ9BCEwC)

### 2. 上下文管理的 Trade-off

推荐 [Claude Code 的网页动画演示](https://code.claude.com/docs/zh-CN/context-window)。

- 短期记忆：在当前对话中智能选择并保留最相关的信息
  - 什么是 `dumb zone`？
  - 上下文压缩：在对话过程中总结历史内容，节省 token 并保持连贯性
- 长期记忆：记住用户偏好、历史对话和项目背景，提升个性化与连续性
  - `AGENT.md`、`CLAUDE.md`：全局和项目级上下文文件
  - Memory 机制：持久化命令历史、用户偏好等信息
- 外部知识库：检索增强生成（RAG）

### 3. 体验不同的 Harness 设计理念

> 什么是 Harness？为什么它是 Agent 设计的核心？

- [OpenClaw 🦞](https://github.com/openclaw/openclaw)、[Hermes Agent ☤](https://github.com/nousresearch/hermes-agent)、[OpenHuman](https://github.com/tinyhumansai/openhuman)、[Pi](https://pi.dev/)
- **Coding Agent**：[Cursor](https://www.cursor.com/)、[Codex](https://openai.com/codex)、[Claude Code](https://code.claude.com/docs)、[OpenCode](https://opencode.ai/)
  - `Hard Core`: 了解 [Pi](https://github.com/earendil-works/pi) 的实现原理



---

## 📜 License  

本项目采用 **MIT 许可证**，欢迎自由修改和使用！  

## 🤝 贡献  

欢迎 Issue & PR！如果你有更好的想法，欢迎贡献代码！  
