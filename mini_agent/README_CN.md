# Mini Agent

这是 `DIY Your AI Agent` 仓库里的最小可运行 Agent 示例，直接使用 Python 和 OpenAI Responses API 展示 ReAct + Tool Calling 的基础闭环。

## 快速开始

在仓库根目录安装依赖并准备环境：

```shell
pip install -r requirements.txt
cp mini_agent/.env.example .env
```

编辑根目录 `.env` 文件，填入你的 API Key、Base URL 和模型名称：

```plaintext
API_KEY=your_api_key_here
BASE_URL=https://api.openai.com/v1
MODEL=your_model_name
```

从仓库根目录运行：

```shell
python .\mini_agent\agent.py
```

输入 `/exit` 或 `/quit` 退出。

## 交互命令

- `/exit`：退出程序。
- `/quit`：退出程序。
- `/bypass`：切换审批绕过模式。开启后，`exec_command` 和 `edit_file` 不再询问确认；再次输入会关闭。

## 当前能力
- 执行 `exec_command` 和 `edit_file` 前默认请求用户批准。
- 内置 4 个本地工具：
  - `read_file`：按 1-based 行号读取文本文件。
  - `edit_file`：按 1-based 行号替换文件中的一段内容，保留其他行。
  - `search_files`：搜索文件内容。
  - `exec_command`：执行 shell 命令。

```markdown
main loop
  ├─ 处理用户命令：/exit /quit /bypass
  └─ agent.run(task)
       └─ run_tool_calls()
            └─ run_tool()
                 ├─ approval_policy.should_approve(name, args)
                 ├─ ask user approve / reject
                 └─ handler(args)
```
## 文件说明

```text
mini_agent/
├── agent.py        # Agent 主循环：模型调用、工具调度、终端交互
├── tools.py        # 工具定义和工具执行函数
└── .env.example    # 环境变量示例
```

## 如何阅读代码

建议从 `agent.py` 开始看：

1. `SYSTEM_PROMPT`：约束 Agent 的基本行为。
2. `Agent.run()`：执行一次用户任务，循环处理模型输出和工具调用。
3. `run_tool_calls()`：把模型的 function call 转成真实工具执行。
4. `register_tool()`：把工具 schema 和 Python handler 绑定起来。

再看 `tools.py`：

1. 每个工具都有一个 JSON schema，告诉模型“这个工具怎么调用”。
2. 每个工具都有一个 Python 函数，负责真正执行。
3. `BUILTIN_TOOLS` 把 schema 和 handler 组合起来，交给 Agent 注册。

## 安全提示

这个示例可以读取和编辑文件，也可以执行 shell 命令。请不要在包含敏感文件的目录中随意测试，也不要把真实 `.env` 提交到 GitHub。
