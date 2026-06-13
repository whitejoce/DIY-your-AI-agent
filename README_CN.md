# DIY Your AI Agent

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-blue">
  <img alt="OpenAI SDK" src="https://img.shields.io/badge/OpenAI%20SDK-1.35%2B-111827">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green">
</p>

**本项目是 [whitejoce/AI-Agent-Toolkit](https://github.com/whitejoce) 技术栈的一部分，专注于 Agent 层。**  
完整技术路线：[RAG](https://github.com/whitejoce/RAG-Demo)（企业知识库） → [Agent](https://github.com/whitejoce/DIY-your-AI-agent) → [Tool Runtime](https://github.com/whitejoce/ToolFlow)（可热加载的MCP Tools平台）
## 🔥 项目简介  

这是一个最小可运行的 AI Agent 示例。它不依赖 LangChain、LangGraph 等框架，项目为轻量级、易读、易修改而生，适合学习 Agent 的基本结构和工具调用机制。


<p align="center">
  <img src="./img/demo.png" alt="DIY Your AI Agent demo" width="900" style="border:1px solid #ccc; border-radius:8px;">
</p>

## Mini Agent

当前仓库里的MVP示例放在 [`mini_agent/`](./mini_agent/) 目录下。

- 使用说明：[mini_agent/README_CN.md](./mini_agent/README_CN.md)
- 入口文件：`mini_agent/agent.py`
- 工具定义：`mini_agent/tools.py`

## 代码结构

```text
.
├── requirements.txt    # Python 依赖
├── mini_agent/
│   ├── agent.py        # Agent 主循环：模型调用、工具调度、终端交互
│   ├── tools.py        # 工具定义和工具执行函数
│   ├── README_*.md     # 说明文档
│   └── .env.example    # 环境变量示例
├── img/demo.png        # 运行截图
├── README_CN.md        # 中文说明
├── README.md           # 英文说明
└── LICENSE
```

## 正式版路线图

保留`Mini Agent`作为学习和测试的基础，正式版逐步增加以下模块：

- `ToolRegistry`：统一管理内置工具、第三方工具和 MCP 工具。
- `ApprovalPolicy`：在执行写文件、执行命令等高风险工具前请求用户确认。
- `ContextManager`：负责短期上下文、长对话压缩和 token 预算。
- `Memory`：保存长期记忆、用户偏好和项目级上下文。

## 安全提示

> 这个仓库目前更适合学习 Agent 的基本结构，日常使用，推荐社区维护的成熟项目



---

## 💡 See Also

### 1. 和SOTA模型交流素材

- LLM API
  - OpenAI [Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses#about-the-responses-api)、`Chat Completions API`
  - Anthropic [Messages API](https://platform.claude.com/docs/zh-CN/build-with-claude/working-with-messages)
- [MCP 协议](https://modelcontextprotocol.io/introduction)、[Skills](https://developers.openai.com/api/docs/guides/skills) 与渐进式披露
- 上下文工程 vs Harness 工程
  - Function Calling、[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)   
- Agentic AI
  - 为什么提示词变得没那么重要了？
  - 可观测性与编排：日志、工具调用记录、错误追踪、性能监控
  - Human-in-the-loop?
- 评分与评测
  - [Artificial Analysis](https://artificialanalysis.ai/models)、[Deep SWE benchmark](https://deepswe.datacurve.ai/)

- Multi-Agent: Agent SDK
  - ADK：`A2A 协议`、`agent.json`
  - LangGraph、LangChain 等框架的设计理念和实现细节
- 衡量 LLM 输出的质量
  - 指标：准确性、完整性、长度、路径

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
