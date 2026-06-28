# Full Agent

`full_agent` 是 `DIY Your AI Agent` 里的可扩展版 Agent runtime。它保留 `mini_agent` 的可读性，但把核心运行时拆成更清晰的模块，方便继续加入长期记忆、Skill 加载、MCP、RAG 和外部工具生态。

这个版本的核心设计原则是：

> **Agent harness 自己实现，外部能力通过 adapter 接入成熟框架。**

也就是说，Agent 的控制面由本项目掌握，包括 loop、上下文、工具调度、审批、安全策略和测试；RAG、MCP、数据连接器等外部能力则优先复用 LangChain、MCP SDK 等成熟项目，再包装成 `ToolProvider` 接入本 runtime。

## 当前能力

- `AgentRuntime`：负责 ReAct loop、模型调用、工具调用、短期上下文和最大轮数保护。
- `OpenAIResponsesModel`：封装 OpenAI Responses API，测试中可替换为 fake model。
- `ToolRegistry` / `ToolExecutor`：统一注册和执行工具，工具名全局唯一。
- `ApprovalPolicy`：对高风险工具执行前请求审批，默认覆盖 `edit_file`、`exec_command`、`remember`。
- `ConversationMemory` / `ContextManager`：保存当前会话，并按字符预算裁剪上下文。
- `MemoryStore`：使用 `.agent/memory.jsonl` 保存长期记忆。
- `SkillLoader`：加载目录型 instruction skill，不动态执行 Python 代码。
- `StaticMCPToolProvider`：提供 MCP provider 接口和测试替身，暂不连接真实 MCP server。
- CLI：通过 `python -m full_agent` 启动交互式终端。

## 快速开始

安装依赖：

```shell
pip install -r requirements.txt
```

配置环境变量：

```plaintext
API_KEY=your_api_key_here
BASE_URL=https://api.openai.com/v1
MODEL=your_model_name
```

启动 full agent：

```shell
python -m full_agent
```

CLI 支持以下命令：

```text
/exit      退出
/quit      退出
/bypass    切换危险工具审批绕过模式
/tools     查看已注册工具
/skills    查看已发现 skill
/memory    查看长期记忆
```

## 架构边界

`full_agent` 不直接把 LangChain 或 LangGraph 作为主 runtime。原因是本项目希望学习和掌握 Agent harness 的关键机制，而不是把核心控制流交给外部框架。

代码实现边界如下：

```text
full_agent owns
  - AgentRuntime
  - tool calling loop
  - context management
  - memory policy
  - approval policy
  - CLI and tests

external frameworks provide
  - RAG loaders / splitters / retrievers / vector stores
  - MCP client/server connection
  - third-party data connectors
  - specialized tool implementations

adapter layer connects them
  - LangChainRAGToolProvider
  - MCPToolProvider
  - other ToolProvider implementations
```

这样可以保持核心代码可读，同时避免重复造 RAG、MCP、向量库和数据连接器这些已经很成熟的基础设施。

## 代码结构

```text
full_agent/
├── __main__.py          # python -m full_agent 入口
├── cli.py               # 终端交互
├── config.py            # AgentConfig
├── runtime.py           # AgentRuntime 主循环
├── model.py             # ModelClient 抽象和 OpenAI Responses 实现
├── context.py           # 短期会话和上下文裁剪
├── memory.py            # JSONL 长期记忆
├── skills.py            # 目录型 skill 加载
├── mcp.py               # MCP provider 协议和静态测试实现
├── approval.py          # 工具审批策略
└── tools/
    ├── base.py          # ToolSpec / ToolRegistry / ToolExecutor
    ├── builtin.py       # mini_agent 内置工具适配
    └── memory_tools.py  # remember / memory_search
```

## ToolProvider 接口

所有外部能力都应该先包装成 `ToolProvider`，再注册到 `ToolRegistry`。

```python
class ToolProvider:
    def load_tools(self):
        ...
```

每个工具使用 `ToolSpec` 描述：

```python
ToolSpec(
    definition={...},          # OpenAI function schema
    handler=callable,          # Python handler
    source="rag:langchain",    # 工具来源
    requires_approval=False,   # 是否需要审批
)
```

这样 runtime 不需要知道工具背后来自本地函数、LangChain retriever、MCP server，还是其他外部服务。

## RAG 接入建议

RAG 不建议在核心 runtime 里从零实现。推荐做一个 adapter，把 LangChain retriever 包装成普通工具：

```text
LangChain retriever
  -> LangChainRAGToolProvider
  -> ToolSpec(name="rag_search")
  -> AgentRuntime
```

建议 `rag_search` 的输入保持简单：

```json
{
  "query": "需要检索的问题",
  "limit": 5
}
```

输出应转换成普通文本或稳定 JSON，避免把 LangChain 内部对象泄漏给 Agent loop。这样后续替换向量库、embedding provider 或 reranker 时，不需要改 `AgentRuntime`。

## MCP 接入建议

当前版本只提供 `MCPToolProvider` 协议和 `StaticMCPToolProvider` 测试替身。真实 MCP 接入建议作为独立 provider 实现：

```text
MCP server
  -> MCP client / LangChain MCP adapter
  -> MCPToolProvider
  -> ToolSpec
  -> AgentRuntime
```

无论 MCP 工具来自哪个 server，进入 runtime 后都应该遵守同一套规则：

- 工具名必须唯一。
- 高风险工具必须标记 `requires_approval=True`。
- 错误应返回可读文本，不应直接中断主 loop。
- 工具输出需要截断，避免撑爆上下文。

## Skill 格式

`SkillLoader` 读取 `.agent/skills/` 下的目录型 skill。每个 skill 至少包含：

```text
.agent/skills/example-skill/
├── skill.json
└── SKILL.md
```

`skill.json` 示例：

```json
{
  "name": "pytest-helper",
  "description": "Help with Python test workflows.",
  "triggers": ["pytest", "test failure"],
  "instructions": "SKILL.md"
}
```

当用户任务命中 `name` 或 `triggers` 时，runtime 会加载对应 `SKILL.md`，并把它作为相关说明注入系统上下文。当前版本不会动态导入或执行 skill 目录里的 Python 代码。

## 长期记忆

长期记忆默认保存在：

```text
.agent/memory.jsonl
```

内置两个记忆工具：

- `remember`：保存长期记忆，默认需要审批。
- `memory_search`：按关键词搜索记忆，大小写不敏感。

`.agent/` 已加入 `.gitignore`，避免本地记忆被误提交。


## TODO

这个版本先稳定核心 runtime 和扩展接口，下一步可以在不改主 loop 的前提下增加：

- `LangChainRAGToolProvider`
- `LangChainMCPToolProvider`
- 官方 MCP SDK provider
- 更完整的日志和 trace
- 更强的上下文压缩策略
